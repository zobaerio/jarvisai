# J.A.R.V.I.S — OpenRouter HTTP 404 troubleshooting (বাংলা)

এই গাইডটি OpenRouter ব্যবহার করার সময় `HTTP 404`, `model not found` বা ভুল endpoint error দেখা দিলে কাজে লাগবে।

## 1. Advanced Settings যাচাই করুন

- **Provider:** OpenAI-compatible / OpenRouter (যে অপশনটি অ্যাপে আছে)
- **Base URL:** `https://openrouter.ai/api/v1`
- **Model:** OpenRouter-এর Models catalog-এ দেখানো সম্পূর্ণ model ID, সাধারণত `provider/model-name` ফরম্যাটে
- **API key:** OpenRouter থেকে পাওয়া key-টি অ্যাপের Settings-এর secure API-key field-এ দিন।

**Base URL-এর শেষে `/chat/completions` যোগ করবেন না।** অ্যাপের client নিজে chat-completions route যোগ করলে URL হবে `https://openrouter.ai/api/v1/chat/completions`। Base URL-এ route যোগ করা থাকলে duplicate path হয়ে 404 হতে পারে।

## 2. মডেল ID ঠিক আছে কি না দেখুন

OpenRouter-এর model ID হুবহু ব্যবহার করুন—শুধু display name বা provider-এর নিজস্ব model alias লিখবেন না। কোনো model আর available না থাকলে catalog থেকে বর্তমানে উপলভ্য model বেছে নিন। Model ID-তে typo, ভুল provider prefix, বা পুরোনো model name থাকলে 404 হতে পারে।

## 3. ধাপে ধাপে পরীক্ষা

1. Settings খুলে Base URL ও model ID ঠিক করুন।
2. API key secure field-এ দিন এবং settings save করুন।
3. অ্যাপের **Test Connection** চালান।
4. এরপর একটি সাধারণ chat prompt দিয়ে real generation পরীক্ষা করুন।
5. Connection test সফল কিন্তু chat ব্যর্থ হলে নির্বাচিত model-এর availability/permissions এবং app log-এর safe diagnostic দেখুন।

## 4. Error দেখে প্রাথমিক ধারণা

- **404 / endpoint not found:** Base URL-এ অতিরিক্ত route, ভুল API path, বা provider endpoint mismatch পরীক্ষা করুন।
- **404 / model not found:** সম্পূর্ণ model ID ও OpenRouter catalog-এ তার availability পরীক্ষা করুন।
- **401 / 403:** API key, account access, provider/model permissions পরীক্ষা করুন।
- **429:** rate limit বা account/provider quota পরীক্ষা করুন।

এই error mapping প্রাথমিক নির্দেশনা—একটি status code থেকেই একমাত্র কারণ নিশ্চিত করা যায় না।

## নিরাপত্তা

- API key README, issue, screenshot, source code বা commit-এ প্রকাশ করবেন না।
- API key-সহ Settings screenshot কাউকে পাঠাবেন না।
- অচেনা endpoint-এ secret key দেবেন না; cloud provider-এর জন্য HTTPS ব্যবহার করুন।
- API key বসালেই সব model, tool-calling বা agent action সমর্থিত হবে—এমন নিশ্চয়তা নেই। বাস্তব chat/task দিয়ে যাচাই করুন।
