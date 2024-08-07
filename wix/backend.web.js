import { Permissions, webMethod } from "wix-web-module";
import wixSecretsBackend from "wix-secrets-backend";

export const getApifyApiKey = webMethod(Permissions.Admin, () => {
  return wixSecretsBackend
    .getSecret("apify_api_key")
    .then((secret) => {
      return secret;
    })
    .catch((error) => {
      console.error(error);
    });
});

export const getOpenAiApiKey = webMethod(Permissions.Admin, () => {
  return wixSecretsBackend
    .getSecret("openai_api_key")
    .then((secret) => {
      return secret;
    })
    .catch((error) => {
      console.error(error);
    });
});