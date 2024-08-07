import {getApifyApiKey, getOpenAiApiKey} from 'backend/ypi.web';
import wixLocation from 'wix-location';

export function button9_click(event) {

    //incredibly messy code incoming that was hacked together for the sake of making this frontend work
    
    let openaiKey, apifyKey;
    let x_username = "";
    let ig_username = "";
    let threads_username = "";
    $w("#progressBar1").targetValue = 100;

    getOpenaiKey().then(key => {
        openaiKey = key;
    }).catch(error => {
        console.error("Error fetching OpenAI key: ", error);
    })

    getApifyKey().then(key => {
        apifyKey = key;
    }).catch(error => {
        console.error("Error fetching Apify key: ", error);
    })

    console.log("Button clicked!");

    x_username = $w("#input1").value;
    ig_username = $w("#input2").value;
    threads_username = $w("#input3").value;

    let numOfAccounts = 0

    if (!x_username) {
        console.log("Did not provide X username");
        x_username = " ";
    } else {
        numOfAccounts = numOfAccounts + 1;
        $w("#resultsXLogo").show();
    }
    if (!ig_username) {
        console.log("Did not provide IG username");
        ig_username = " ";
    } else {
        numOfAccounts = numOfAccounts + 1;
        $w("#resultsInstagramLogo").show();
    }
    if (!threads_username) {
        console.log("Did not provide Threads username");
        threads_username = " ";
    } else {
        numOfAccounts = numOfAccounts + 1;
        $w("#resultsThreadsLogo").show();
    }

    if (numOfAccounts > 1) {
        $w("#analyzingheader").text = "Analyzing your profiles"
    } else if (numOfAccounts === 1) {
        $w("#analyzingheader").text = "Analyzing your profile"
    } else if (numOfAccounts === 0) {
        $w("#missingfieldserror").show();
        return;
    }


    console.log("x_username:", x_username);
    console.log("ig_username:", ig_username);
    console.log("threads_username:", threads_username);

    const messages = [
        "Most Americans believe it’s impossible to avoid companies and the government collecting their data (Pew Research)",
        "1 in 4 Americans are asked to agree to a privacy policy every day (Pew Research)",
        "Two-thirds of global consumers feel that tech companies have too much control over their data (YouGov)",
        "Almost half of free iOS apps collect user data (42matters)",
        "Nearly half of data breaches include customer names, email addresses, and passwords (IBM)",
        "Phishing attacks rose 29% in 2021 compared to 2020. (Zscaler)",
        "84% of people post personal information to their social media accounts every week, with two-fifths (42%) posting every day (Tessian)",
        "55% of respondents admit they have public profiles on Facebook and just one third (32%) say their Instagram accounts are private (HackerOne)"
    ]
    let messageIndex = 0;

    function updateLoadingMessage() {
        $w("#facts").text = messages[messageIndex];
        messageIndex = (messageIndex + 1) % messages.length;
    }

    $w("#getinfobox").hide("fade", { duration: 500 })
        .then(() => $w("#loadingbox").show("fade", { duration: 500 }));

    // Start progress bar at initial value
    $w("#progressBar1").value = 0;
    $w("#progressBar1").value = 10;

    let interval = 5000;

    if (numOfAccounts === 1){
        interval = 3500;
    } else if (numOfAccounts === 2) {
        interval = 5000;
    } else if (numOfAccounts === 3) {
        interval = 10000;
    }

    if (ig_username != " ") {
        interval = interval + 5000;
    }

    // Simulate progress update while waiting for the result
    let progressValue = 10;
    const progressInterval = setInterval(() => {
        progressValue += 5;
        $w("#progressBar1").value = progressValue;

        if (progressValue >= 100) {
            clearInterval(progressInterval);
        }
    }, interval); // Update every second

    const messageInterval = setInterval(updateLoadingMessage, 5000);

  // Fetch both keys concurrently and wait for both to complete
  Promise.all([getOpenaiKey(), getApifyKey()])
    .then(([openaiKey, apifyKey]) => {
      // Now both keys are available
      return fetch('https://serenitylater.pythonanywhere.com/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          x_username,
          ig_username,
          threads_username,
          apify_api_key: apifyKey,
          openai_api_key: openaiKey
        })
      });
    })
    .then(response => {
      if (!response.ok) {
        return response.text().then(text => { throw new Error(text); });
      }
      return response.json();
    })
    .then(data => {
      $w("#progressBar1").value = 100;
      $w("#loadingbox").hide("fade", { duration: 200 }).then(() => $w("#resultsbox").show("fade", { duration: 700 }));

      clearInterval(progressInterval);
      let backupPfp = "https://static-00.iconduck.com/assets.00/profile-default-icon-2048x2045-u3j7s5nj.png";

      console.log('Result:', data.concated_summaries);
      console.log('Profile pic url: ', data.profile_pic);
      let profile_pic = data.profile_pic;
      let full_name = data.full_name;
      let is_verified = data.is_verified;
      let categorized_risks = data.categorized_risks;
      if (profile_pic !== " "){ //pfp exists
          if (ig_username != " " && numOfAccounts == 1){ // if IG is provided and is the only platform, we dont get a pfp
            setImageSource(backupPfp);
          } else{
            setImageSource(profile_pic);
          }
      }
      $w("#fullName").text = full_name;

      if (is_verified === "True"){
          $w("#verifiedTick").show();
      }

      $w('#resultsplace').text = data.concated_summaries;

     let advice = "Based on information collected from your profile, you should consider the following risks that may be posed:"
     let linkToAdvice = "www.yourpublicimage.com/categoriesofrisk"
     let numOfRisks = 0;
     categorized_risks = categorized_risks.toLowerCase()

      if (categorized_risks.includes("personal")) {
          advice += "\n\nPersonal Safety: Focus on limiting location sharing, including geotagging, and insights into your personal life. This can unintentionally inform a malicious user of potential security question answers, or allow them to impersonate you if trying to perform an account takeover via customer service.";
          numOfRisks += 1;
      }
      if (categorized_risks.includes("privacy")) {
          advice += "\n\nPrivacy: Consider updating privacy settings on your account and consider personal privacy risks including location sharing. This coincides with personal risks, but also places an importance on making sure you're doing your due diligence with the tools provided to you by the platform. Having a private account can effectively prevent an attacker from easily discovering information about you, or from us (and many others) through scraping.";
          numOfRisks += 1;

      }    
      if (categorized_risks.includes("professional")) {
          if (is_verified === "True"){
            advice += "\n\nProfessional: Normally, we'd say to separate professional and personal profiles. While it is true that exposing too much information puts you at risk of impersonation or spear phishing, it seems you are 'Verified' on at least one of the platforms you provided, which might mean that you are a public figure! It is much more difficult to separate your professional and personal details, but remember that it might even more important to watch what you post because of the number of eyes already on you. Current locations can be risky, such as sharing that you are at a coffee shop or airport, so it is better to delay these posts for later, like when you've already left a location.";
          }
          else{
            advice += "\n\nProfessional: Separate professional and personal profiles. Maintain a professional online presence and secure workplace-related information. Exposing too much information puts you at risk of impersonation or spear phishing. If an attacker knows where you work and what you do for work, this can provide significant leverage in understanding what they can gain from you.";
            numOfRisks += 1;
          }
      }
      if (categorized_risks.includes("financial")) {
          advice += "\n\nFinancial: Avoid sharing your financial situation or financial opportunities. This may provide an incentive for someone to target you. If a malicious user can see that you're wealthy, they may be more incentivized to target you. Additionally, if a malicious user can see that you are financially struggling, they can also use that as an incentive to manipulate you. Financial information is very personal and you should avoid sharing it publicly.";
          numOfRisks += 1;

      }
      if (categorized_risks.includes("psychological")) {
          advice += "\n\nPsychological: Avoid sharing emotional challenges and conflicts with other individuals. This opens up opportunities for phishing people you know, which can lead to phishing you. An attacker wants leverage against you. This can include your weaknesses, your struggles, or things that make you vulnerable. If you expose too many personal conflicts, you may be giving an attacker opportunities to take advantage of your situation and people you involve.";
          numOfRisks += 1;

      }  
      if (numOfRisks == 0) {
          advice += "\n\nPersonal Safety: Focus on limiting location sharing, including geotagging, and insights into your personal life. This can unintentionally inform a malicious user of potential security question answers, or allow them to impersonate you if trying to perform an account takeover via customer service." + "\n\nPrivacy: Consider updating privacy settings on your account and consider personal privacy risks including location sharing. This coincides with personal risks, but also places an importance on making sure you're doing your due diligence with the tools provided to you by the platform. Having a private account can effectively prevent an attacker from easily discovering information about you, or from us (and many others) through scraping.";
      }
    
      advice += "\n\nVisit our Internet Safety Guide and Data Privacy Tips for more information."

      $w("#advicerisks").text = advice;
    })
    .catch(error => {
      console.error('Velo-side Error:', error);
      $w("#loadingbox").hide("fade", { duration: 500 }).then(() => $w("#ohnoerrorbox").show("fade", { duration: 500 }));
    });
}

export function setImageSource(imageUrl) {
    $w("#profilepic").src = imageUrl;
}

async function getOpenaiKey() {
    try {
        console.log("Calling getApiKey...");
        const openaiKey = await getOpenAiApiKey();
        return openaiKey
        // Use the API key for your API requests
    } catch (error) {
        console.error('Error using API key:', error);
    }
}

async function getApifyKey() {
    try {
        console.log("Calling getApiKey...");
        const apifyKey = await getApifyApiKey();
        return apifyKey
        // Use the API key for your API requests
    } catch (error) {
        console.error('Error using API key:', error);
    }
}
