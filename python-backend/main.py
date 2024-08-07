from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS, cross_origin
import pandas as pd
from apify_client import ApifyClient
import os
import logging
from openai import OpenAI
from datetime import datetime

progress_file = "path_to_progress_file"

app = Flask(__name__)
progress_blueprint = Blueprint('progress_status', __name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/run', methods=['POST'])
@cross_origin()
def run():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        x_username = data.get('x_username')
        ig_username = data.get('ig_username')
        threads_username = data.get('threads_username')
        apify_api_key = data.get('apify_api_key')
        openai_api_key = data.get('openai_api_key')

        if not x_username or not ig_username or not threads_username:
            return jsonify({"error": "Missing parameters"}), 400

        results = main(x_username, ig_username, threads_username, apify_api_key, openai_api_key)
        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    with open(progress_file, 'r') as f:
        status = f.read()
    return jsonify({"status": status})


def update_progress(status):
    with open(progress_file,'w') as f:
        f.write(status)

@app.route('/test', methods=['POST'])
def test():
    return jsonify({"concated_summaries": "This was a test run.", "profile_pic": "https://cdn1.picuki.com/hosted-by-instagram/q/yep6IPkO1EBGZyPbcMUXyOZUj6M=.jpeg"});

def analyzing_ig_posts(general_user_info, cleaned_instagram, no_extra_info_please, openai_key):
    update_progress("80")
    app.logger.info("ANALYZING INSTAGRAM POST INFO...")
    summarized_ig_post_info = ""
    cleaned_instagram['post_analysis'] = ""
    for index, row in cleaned_instagram.iterrows():
        important_fields = ['caption','image']
        if row['caption'] is not None and len(row['caption']) > 0:
            ig_post = row['caption']
        else:
            ig_post = " "
        picture = row['image']
        is_picture = True

        ig_prompt = "I am providing the caption and picture from an Instagram post a user posted. In maximum two sentences, tell me what you deduce from this post." + no_extra_info_please
        app.logger.debug("Querying ChatGPT...")
        ig_post_analysis = query_chatgpt(openai_key=openai_key, is_picture=is_picture, prompt=ig_prompt, text_content=ig_post, image_link=picture)
        summarized_ig_post_info = summarized_ig_post_info + '. ' + ig_post_analysis
        cleaned_instagram.loc[index, 'post_analysis'] = ig_post_analysis

    ig_post_summary_prompt="I am providing some information I gathered about a user's Instagram posts. Summarize this information into maximum 3 sentences to tell me what you can deduce from this person by analyzing the information. I want you to describe it as if you are speaking to the user directly. Additionally, based on the types of information they're sharing, I want you to categorize their sharing risk as mostly personal, privacy, professional, financial, psychological. Also for context, the user's name is: " + str(general_user_info['full_name']) + no_extra_info_please
    app.logger.debug("Querying ChatGPT...")
    summarized_ig_post_info = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=ig_post_summary_prompt, text_content=summarized_ig_post_info, image_link="")

    return cleaned_instagram, summarized_ig_post_info

def analyzing_threads_posts(general_user_info, cleaned_threads, no_extra_info_please, openai_key):
    update_progress("90")
    app.logger.info("ANALYZING THREADS POST INFO...")
    summarized_threads_post_info = ""
    cleaned_threads['thread_analysis'] = ""
    for index, row in cleaned_threads.iterrows():
        important_fields = ['caption','image']
        #caption = row['caption']['text']

        if row['caption'] is not None:
            if len(row['caption']) > 0:
                caption = row['caption']['text']
            else:
                caption = " "
        else:
            caption = " "

        if len(row['image']['candidates']) != 0:
            image = row['image']['candidates'][0]['url']
        else:
            image = ""
        if caption is not None and len(caption) > 0:
            threads_post = caption
        else:
            threads_post = " "
        if image is not None and len(image) > 0:
            if 'null.jpg' not in image:
                picture = image
            else:
                picture = ""
        else:
            picture = ""

        if picture == "":
            is_picture = False
        else:
            is_picture = True

        if is_picture:
            threads_prompt = "I am providing the text and picture from a social media post a user posted. In maximum two sentences, tell me what you deduce from this post." + no_extra_info_please
        else:
            threads_prompt = "I am providing the text from a social media post a user posted. In maximum two sentences, tell me what you deduce from this post." + no_extra_info_please

        app.logger.debug("Querying ChatGPT...")
        threads_post_analysis = query_chatgpt(openai_key=openai_key, is_picture=is_picture, prompt=threads_prompt, text_content=threads_post, image_link=picture)
        summarized_threads_post_info = summarized_threads_post_info + '. ' + threads_post_analysis
        cleaned_threads.at[index, 'threads_post_analysis'] = threads_post_analysis

    threads_post_summary_prompt="I am providing some information I gathered about a user's social media posts. Summarize this information into maximum 3 sentences to tell me what you can deduce from this person by analyzing the information. I want you to describe it as if you are speaking to the user directly. Additionally, based on the types of information they're sharing, I want you to categorize their sharing risk as mostly personal, privacy, professional, financial, psychological. Also for context, the user's name is: " + str(general_user_info['full_name']) + no_extra_info_please
    app.logger.debug("Querying ChatGPT...")
    summarized_threads_post_info = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=threads_post_summary_prompt, text_content=summarized_threads_post_info, image_link="")

    return cleaned_threads, summarized_threads_post_info

def analyzing_x_posts(general_user_info, cleaned_x, no_extra_info_please, openai_key):
    update_progress("70")
    app.logger.info("ANALYZING X POST INFO...")
    summarized_tweet_info = ""
    cleaned_x['tweet_analysis'] = ""
    for index, row in cleaned_x.iterrows():
        important_fields = ['caption','photosUrl']
        if row['caption'] is not None and len(row['caption']) > 0:
            tweet = row['caption']
        else:
            tweet = " "
        if len(row['photosUrl']) > 0: # eval picture into list and pick first one
            picture = row['photosUrl'][0]
        else:
            picture = ""

        if picture == "":
            is_picture = False
        else:
            is_picture = True

        if is_picture and tweet != " ": # picture and tweet exists
            x_prompt = "I am providing the text and picture from a Tweet a user posted. In maximum two sentences, tell me what you deduce from this tweet." + no_extra_info_please
        elif not is_picture and tweet != " ": # no picture, but tweet exists
            x_prompt = "I am providing the text from a Tweet a user posted. In maximum two sentences, tell me what you deduce from this tweet." + no_extra_info_please
        elif is_picture and tweet == " ": # picture exists, but no tweet
            x_prompt = "I am providing the picture from a Tweet a user posted. In maximum two sentences, tell me what you deduce from this picture." + no_extra_info_please
        else: # no picture and no tweet
            continue

        app.logger.debug("Querying ChatGPT...")
        tweet_analysis = query_chatgpt(openai_key=openai_key, is_picture=is_picture, prompt=x_prompt, text_content=tweet, image_link=picture)

        summarized_tweet_info = summarized_tweet_info + '. ' + tweet_analysis
        cleaned_x.loc[index, 'tweet_analysis'] = tweet_analysis

    tweet_summary_prompt="I am providing some information I gathered about a user's Tweets. Summarize this information into maximum 3 sentences to tell me what you can deduce from this person by analyzing the information. I want you to describe it as if you are speaking to the user directly. Additionally, based on the types of information they're sharing, I want you to categorize their sharing risk as mostly personal, privacy, professional, financial, psychological. Also for context, the user's name is: " + str(general_user_info['full_name']) + no_extra_info_please
    app.logger.debug("Querying ChatGPT...")
    summarized_tweet_info = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=tweet_summary_prompt, text_content=summarized_tweet_info, image_link="")

    return cleaned_x, summarized_tweet_info

def analyzing_posts(general_user_info, platforms_user_is_on, cleaned_x, cleaned_instagram, cleaned_threads, no_extra_info_please, openai_key):
    update_progress("60")
    app.logger.info("ANALYZING POSTS INFO...")
    summarized_post_info = {"X": "", "Instagram": "", "Threads": ""}
    for platform in platforms_user_is_on:
        if platform == "X":
            cleaned_x, summarized_tweet_info = analyzing_x_posts(general_user_info, cleaned_x, no_extra_info_please, openai_key)
            summarized_post_info["X"] = (summarized_tweet_info)
        elif platform == "Instagram":
            cleaned_instagram, summarized_ig_post_info = analyzing_ig_posts(general_user_info, cleaned_instagram, no_extra_info_please, openai_key)
            summarized_post_info["Instagram"] = (summarized_ig_post_info)
        elif platform == "Threads":
            cleaned_threads, summarized_threads_post_info = analyzing_threads_posts(general_user_info, cleaned_threads, no_extra_info_please, openai_key)
            summarized_post_info["Threads"] = (summarized_threads_post_info)

    return cleaned_x, cleaned_instagram, cleaned_threads, summarized_post_info


def query_chatgpt(openai_key, is_picture, prompt, text_content="", image_link=""):
    client = OpenAI(
        api_key = openai_key
    )
    if is_picture:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": image_link,
                    },
                    },
                ],
                }
            ],
            max_tokens=300,
        )
        final_response_content = response.choices[0].message.content


    else:
        text_prompt = prompt + text_content
        response = client.chat.completions.create(
            messages=[
                {'role': 'user', 'content': text_prompt}
            ],
            model='gpt-3.5-turbo',
        )
        final_response_content = response.choices[0].message.content


    return final_response_content

def analyzing_general_user_info(general_user_info, openai_key, no_extra_info_please):
    general_user_info['bio_analysis'] = ""
    general_user_info['pfp_analysis'] = ""
    summarized_user_info = ""

    update_progress("40")
    app.logger.info("ANALYZING GENERAL USER INFO...")
    for index, row in general_user_info.iterrows():

        if len(row['bio']) < 1:
            bio = ""
        else:
            bio = row['bio']

        if len(row['profile_picture']) < 1:
            profile_picture = ""
        else:
            profile_picture = row['profile_picture']

        if bio == "" and profile_picture == "": # no bio or profile picture
            continue
        elif bio == "" and profile_picture != "": # only a pfp
            profile_picture_prompt="I am providing a profile picture of an individual. Tell me in one sentence what you can deduce from this person by analyzing the photo." + no_extra_info_please
            app.logger.debug("Querying ChatGPT...")
            profile_picture_analysis = query_chatgpt(openai_key=openai_key, is_picture=True, prompt=profile_picture_prompt, text_content="", image_link=profile_picture)
            general_user_info.loc[index, 'pfp_analysis'] = profile_picture_analysis
            summarized_user_info =  summarized_user_info + '.' + profile_picture_analysis
        elif profile_picture == "" and bio != "": # only a bio
            bio_prompt="I am providing a social media bio of an individual. Tell me in maximum 3 sentences what you can deduce from this person by reading the bio." + no_extra_info_please
            app.logger.debug("Querying ChatGPT...")
            bio_analysis = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=bio_prompt, text_content=bio, image_link="")
            general_user_info.loc[index, 'bio_analysis'] = bio_analysis
            summarized_user_info = summarized_user_info + '.' + bio_analysis

        else:
            profile_picture_prompt="I am providing a profile picture of an individual. Tell me in one sentence what you can deduce from this person by analyzing the photo." + no_extra_info_please
            app.logger.debug("Querying ChatGPT...")
            profile_picture_analysis = query_chatgpt(openai_key=openai_key, is_picture=True, prompt=profile_picture_prompt, text_content="", image_link=profile_picture)
            general_user_info.loc[index, 'pfp_analysis'] = profile_picture_analysis
            summarized_user_info =  summarized_user_info + '.' + profile_picture_analysis

            bio_prompt="I am providing a social media bio of an individual. Tell me in maximum 3 sentences what you can deduce from this person by reading the bio." + no_extra_info_please
            app.logger.debug("Querying ChatGPT...")
            bio_analysis = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=bio_prompt, text_content=bio, image_link="")
            general_user_info.loc[index, 'bio_analysis'] = bio_analysis
            summarized_user_info = summarized_user_info + '.' + bio_analysis

    update_progress("50")
    user_summary_prompt="I am providing some information I found out about a user. Summarize this information into maximum 3 sentences to tell me what you can deduce from this person by analyzing the photo. I want you to describe it as if you are speaking to the user directly. Also for context, the user's name is: " + str(general_user_info['full_name']) + no_extra_info_please
    app.logger.debug("Querying ChatGPT...")
    summarized_user_info = query_chatgpt(openai_key=openai_key, is_picture=False, prompt=user_summary_prompt, text_content=summarized_user_info, image_link="")

    return general_user_info, summarized_user_info

def clean_data_threads(raw_threads, general_user_info):
    #raw_threads.drop(['video_versions', 'text_post_app_info', 'reply_count', 'original_width','original_height', 'carousel_media', 'carousel_media_count','pk', 'has_audio', 'taken_at', 'code', 'media_overlay_info'], axis=1, inplace=True)
    threads = raw_threads.copy()

    threads = threads.rename(columns={
        'like_count': 'likesCount',
        'image_versions2': 'image'
        # Add other necessary renames for df3
    })

    threads2 = threads['user']
    threads['profilePicUrl'] = threads2[0]['profile_pic_url']
    threads['userName'] = threads2[0]['username']
    threads['verified'] = threads2[0]['is_verified']
    #threads['image'] = threads['image'][0].split('url')[1].split("',")[0].split(": '")[1]

    general_user_info["platform"].append("Threads")
    general_user_info["username"].append(threads['userName'][0])
    general_user_info["full_name"].append(threads['userName'][0])
    general_user_info["profile_picture"].append(threads['profilePicUrl'][0])
    general_user_info["bio"].append("")
    general_user_info["is_verified"].append(threads['verified'][0])

    threads.drop(['user'], axis=1, inplace=True)
    threads.drop(['userName'], axis=1, inplace=True)
    threads.drop(['profilePicUrl'], axis=1, inplace=True)
    threads.drop(['verified'], axis=1, inplace=True)

    return threads, general_user_info

def clean_data_instagram(raw_instagram, general_user_info):
    #raw_instagram.drop(['videoUrl','images','taggedUsers','coauthorProducers','musicInfo', 'latestComments','dimensionsHeight', 'dimensionsWidth', 'url', 'commentsCount', 'videoPlayCount', 'locationId', 'productType', 'videoDuration', 'isPinned', 'childPosts', 'ownerId', 'isSponsored'], axis=1, inplace=True)

    ig = raw_instagram.copy()

    ig = ig.rename(columns={
        'inputUrl': 'profileUrl',
        'type': 'mediaType',
        'url': 'profileUrl',
        'alt': 'activityDescription',
        'ownerUsername': 'userName',
        'ownerFullname': 'fullName',
        'timestamp': 'date',
        'locationName': 'location',
        'displayUrl': 'image'
    })

    # Convert the date column to datetime and format to "YYYY-MM-DD"
    ig['date'] = pd.to_datetime(ig['date']).dt.strftime('%Y-%m-%d')

    general_user_info["platform"].append("Instagram")
    general_user_info["username"].append(ig['userName'][0])
    general_user_info["full_name"].append(ig['ownerFullName'][0])
    general_user_info["profile_picture"].append("")
    general_user_info["bio"].append("")
    general_user_info["is_verified"].append("")

    ig.drop(['userName'], axis=1, inplace=True)
    ig.drop(['ownerFullName'], axis=1, inplace=True)

    return ig, general_user_info

def clean_data_x(raw_x, general_user_info):
    #raw_x.drop(['isRetweet','isQuote','lang','twitterUrl','source','retweetCount', 'replyCount', 'likeCount', 'isReply', 'bookmarkCount', 'quoteCount', 'card', 'isConversationControlled'], axis=1, inplace=True)
    x = raw_x.copy()

    x = x.rename(columns={
        'createdAt': 'date',
        'type': 'mediaType',
        'url': 'profileUrl',
        'author': 'userInfo',
        'place': 'location',
        'media': 'photosUrl',
        'text': 'caption'
    })

    # Function to convert date string to "YYYY-MM-DD"
    def convert_date(date_str):
        date_obj = datetime.strptime(date_str, '%a %b %d %H:%M:%S %z %Y')
        return date_obj.strftime('%Y-%m-%d')

    # Apply the function to the column
    x['date'] = x['date'].apply(convert_date)

    x2 = x['userInfo'][0]
    x['userName']= x2['userName']
    x['fullName']= x2['name']
    x['verified']= x2['isVerified']
    x['profilePicUrl']= x2['profilePicture']
    x['bio']= x2['description']

    general_user_info["platform"].append("X")
    general_user_info["username"].append(x['userName'][0])
    general_user_info["full_name"].append(x['fullName'][0])
    general_user_info["profile_picture"].append(x['profilePicUrl'][0])
    general_user_info["bio"].append(x['bio'][0])
    general_user_info["is_verified"].append(x['verified'][0])

    x.drop(['entities'], axis=1, inplace=True)
    x.drop(['extendedEntities'], axis=1, inplace=True)
    x.drop(['userInfo'], axis=1, inplace=True)
    x.drop(['userName'], axis=1, inplace=True)
    x.drop(['profilePicUrl'], axis=1, inplace=True)
    x.drop(['bio'], axis=1, inplace=True)
    x.drop(['fullName'], axis=1, inplace=True)
    x.drop(['verified'], axis=1, inplace=True)

    return x, general_user_info

def cleaning_and_getting_general_info(platforms_user_is_on, x_df, instagram_df, threads_df, general_user_info):
    cleaned_x = ""
    cleaned_instagram = ""
    cleaned_threads = ""

    for platform in platforms_user_is_on:
        if platform == "X":
            app.logger.info("CLEANING X DATA...")
            cleaned_x, general_user_info = clean_data_x(x_df, general_user_info)
        elif platform == "Instagram":
            app.logger.info("CLEANING INSTAGRAM DATA...")
            cleaned_instagram, general_user_info = clean_data_instagram(instagram_df, general_user_info)
        if platform == "Threads":
            app.logger.info("CLEANING THREADS DATA...")
            cleaned_threads, general_user_info = clean_data_threads(threads_df, general_user_info)

    general_user_info = pd.DataFrame.from_dict(general_user_info)
    return general_user_info, cleaned_x, cleaned_instagram, cleaned_threads, platforms_user_is_on

def scrape_x(username, client):
    url = "https://x.com/" + username + "/"

    # Prepare the Actor input
    run_input = {
        "startUrls": [
            url,
        ],
        "twitterHandles": [
            username,
        ],
        "maxItems": 10,
        "sort": "Latest",
        "tweetLanguage": "en",
    }

    # Run the Actor and wait for it to finish
    run = client.actor("61RPP7dywgiy0JPD0").call(run_input=run_input)

    x_gathered_data = []

    # Fetch and print Actor results from the run's dataset (if there are any)
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        x_gathered_data.append(item)

    return x_gathered_data

def scrape_instagram(username, client):
    url = "https://www.instagram.com/" + username + "/"

    # Prepare the Actor input
    run_input = {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": 10,
        "searchType": "hashtag",
        "searchLimit": 1,
        "addParentData": False,
    }

    # Run the Actor and wait for it to finish
    run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    instagram_gathered_data = []

    # Fetch and print Actor results from the run's dataset (if there are any)
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        instagram_gathered_data.append(item)

    return instagram_gathered_data

def scrape_threads(username, client):
    url = "https://www.threads.net/@" + username

    # Prepare the Actor input
    run_input = { "urls": [
            url
        ] }

    # Run the Actor and wait for it to finish
    run = client.actor("LnCvmgElmmlHN1gvZ").call(run_input=run_input)

    threads_gathered_data = []

    # Fetch and print Actor results from the run's dataset (if there are any)
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        threads_gathered_data.append(item)

    return threads_gathered_data


def get_user_info(apify_key, platforms_user_is_on, usernames):
    client = ApifyClient(apify_key)

    for key, value in usernames.items():
        if key == "X":
            if value != " ": # X account exists
                update_progress("10")
                app.logger.info("SCRAPING X DATA...")
                platforms_user_is_on.append("X")
                collected_x_data = scrape_x(value, client)
                x_df = pd.DataFrame(collected_x_data)
            else: # X account does not exist
                x_df = ""
        elif key == "Instagram":
            if value != " ": # IG account exists
                update_progress("20")
                app.logger.info("SCRAPING INSTAGRAM DATA...")
                platforms_user_is_on.append("Instagram")
                collected_instagram_data = scrape_instagram(value, client)
                instagram_df = pd.DataFrame(collected_instagram_data)
            else: # IG account does not exist
                instagram_df = ""
        elif key == "Threads":
            if value != " ": # Threads account exists
                update_progress("30")
                app.logger.info("SCRAPING THREADS DATA...")
                platforms_user_is_on.append("Threads")
                collected_threads_data = scrape_threads(value, client)
                threads_df = pd.DataFrame(collected_threads_data)
            else:
                threads_df = ""

    return x_df, instagram_df, threads_df

# Route to get the current progress status
@progress_blueprint.route('/task_status', methods=['GET'])
def get_task_status():
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            status = f.read().strip()
        return jsonify({"status": status}), 200
    return jsonify({"status": "No progress available"}), 200

def main(x_username, ig_username, threads_username, apify_api_key, openai_api_key):
    # Defining variables
    no_extra_info_please = " Give me the information directly without any introductory sentences."
    supported_platforms = ["X", "Instagram", "Threads"]
    platforms_user_is_on = []
    usernames = {"X": x_username, "Instagram": ig_username, "Threads": threads_username}
    general_user_info = {"username" : [], "full_name": [], "profile_picture": [], "bio": [], "is_verified": [], "platform": []}
    categories_of_risks = ["personal_safety", "privacy", "professional", "financial", "psychological"]

    # Verify accounts and scrape
    x_df, instagram_df, threads_df = get_user_info(apify_api_key, platforms_user_is_on, usernames)

    ## Now we clean the dataframes
    general_user_info, cleaned_x, cleaned_instagram, cleaned_threads, platforms_user_is_on = cleaning_and_getting_general_info(platforms_user_is_on, x_df, instagram_df, threads_df, general_user_info)

    ## General user info queries
    general_user_info, summarized_user_info = analyzing_general_user_info(general_user_info, openai_api_key, no_extra_info_please)

    ## post queries
    cleaned_x, cleaned_instagram, cleaned_threads, summarized_post_info = analyzing_posts(general_user_info, platforms_user_is_on, cleaned_x, cleaned_instagram, cleaned_threads, no_extra_info_please, openai_api_key)

    ## Display found information
    concated_summaries = summarized_user_info
    for i in platforms_user_is_on:
        if i == "X":
            concated_summaries += "\n\n" + "Summary from X: \n\n" + summarized_post_info["X"]
        elif i == "Instagram":
            concated_summaries += "\n\n" + "Summary from Instagram: \n\n" + summarized_post_info["Instagram"]
        elif i == "Threads":
            concated_summaries += "\n\n" + "Summary from Threads: \n\n" + summarized_post_info["Threads"]

    risk_prompt = "I am providing some information about a user on social media. Based on the types of information they're sharing, I want you to categorize their sharing risk as mostly personal, privacy, professional, financial, psychological. Provide your answer in a list of maximum 3 categories only."
    categorized_risks = query_chatgpt(openai_key=openai_api_key, is_picture=False, prompt=risk_prompt, text_content=concated_summaries, image_link="")

    profile_pic = general_user_info['profile_picture']
    full_name = general_user_info['full_name'].values[0]
    is_verified = general_user_info['is_verified'].values.tolist()
    str_is_verified = "False"
    if len(profile_pic) == 0:
        profile_pic = " "
    else:
        profile_pic = profile_pic[0]

    for i in is_verified:
        if i is True:
            str_is_verified = "True"
            break

    print("Summarized user info")
    print(full_name)
    print(profile_pic)
    print(is_verified)
    app.logger.info(categorized_risks)

    print(categorized_risks)
    return {"concated_summaries": concated_summaries, "profile_pic": profile_pic, "full_name": full_name, "is_verified": str_is_verified, "categorized_risks": categorized_risks}
