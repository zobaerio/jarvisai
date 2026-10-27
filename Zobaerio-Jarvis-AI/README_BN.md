# ORVIX AI Desktop Assistant — বাংলা Setup Guide

**সংস্করণ:** 1.7.3 — voice timeout reliability

## সহজ Windows Installer (প্রস্তাবিত)

**সর্বশেষ installer ডাউনলোড:** https://github.com/zobaerio/orvixai/releases/latest

1. উপরের Releases পেজ খোলো এবং **Assets** থেকে `ORVIX-AI-Setup.exe` ডাউনলোড করো।
2. ডাউনলোড করা ফাইলটিতে double-click করো। এটি বর্তমান Windows user-এর জন্য ইনস্টল হবে; সাধারণত Administrator permission লাগবে না।
3. Setup শেষ হলে Start Menu থেকে **ORVIX AI Desktop Assistant** চালু করো। Setup-এর সময় চাইলে Desktop shortcut তৈরি করার option নির্বাচন করো।
4. নতুন version install/upgrade করলেও settings ও task history app installation folder-এর বাইরে রাখার জন্য design করা হয়েছে। Uninstall করার আগে গুরুত্বপূর্ণ তথ্যের backup রাখা ভালো।

**নিরাপত্তা নোট:** Installer বর্তমানে digitally signed নয়। তাই Windows SmartScreen unknown-publisher warning দেখাতে পারে। ফাইলটি অবশ্যই এই repository-এর Releases পেজ থেকে এসেছে কি না যাচাই করবে; Windows security globally বন্ধ করবে না। Release-এ SHA-256 checksum file-ও দেওয়া থাকবে।

যদি Releases পেজে installer না থাকে, তাহলে release এখনো publish হয়নি। সাময়িক CI build GitHub Actions → সফল Windows Installer Package run → Artifacts-এ থাকতে পারে; CI artifact স্থায়ী নয় এবং মেয়াদ শেষে মুছে যায়। স্থায়ী download-এর জন্য Releases ব্যবহার করো।

## Source থেকে install (বিকল্প)

Task History-তে এখন প্রতিটি tool action-এর নাম, শুরু হওয়ার সময় ও অবস্থা দেখা যাবে। Audit log-এ tool arguments বা result content রাখা হয় না। App চলার মাঝখানে বন্ধ হয়ে গেলে চলমান action-কে `INTERRUPTED` এবং ফলাফল অনিশ্চিত হিসেবে চিহ্নিত করা হবে; সেটি নিজে থেকে পুনরায় চালানো হবে না।

## নতুন: Step-by-step Task Execution

জটিল অনুরোধের জন্য J.A.R.V.I.S প্রথমে tool ছাড়া একটি সীমিত plan তৈরি করে, তারপর plan-এর প্রতিটি ধাপ আলাদা AI turn-এ চালায়। প্রতিটি ধাপে Task History-তে status, expected evidence type, start/finish time, duration, attempt count, evidence type এবং verification note দেখা যাবে। Tool audit entry-গুলো plan step-এর সঙ্গে link করা হয়, কিন্তু tool arguments বা output payload audit log-এ রাখা হয় না।

**Completion যাচাই:** শুধু AI-এর “কাজ হয়ে গেছে” বলা দিয়ে কোনো file/app/window পরিবর্তনের ধাপ completed হবে না। Text deliverable-এর step text response দিয়ে শেষ হতে পারে; read-only inspection-এর step-এ বাস্তব read-only tool result লাগবে; state-changing step-এ সংশ্লিষ্ট target-এর positive `verify_local_action` result লাগবে; expected target-এর সঙ্গে verification মিলতে হবে, আর পরে আরেকটি state change হলে আগের verification evidence বাতিল হবে। Verification না পাওয়া, tool failure, cancellation বা shared ১২টি tool-action limit পৌঁছালে plan থেমে যায় এবং পরের ধাপ চালু হয় না। Unsupported বা ambiguous action-এ Task History-তে `UNVERIFIED` দেখা যেতে পারে—এর মানে কাজ হয়েছে এমন প্রমাণ পাওয়া যায়নি।

App restart হলে চলমান step `UNVERIFIED` এবং শুরু না হওয়া pending step `SKIPPED` হিসেবে চিহ্নিত হয়; কোনো action নিজে থেকে replay বা resume হয় না। Task History-এর **Resume Plan** বাটনে explicit confirmation দিলে নতুন task record তৈরি হয়; আগের completed step-গুলো replay হয় না, প্রথম unfinished step থেকে শুরু হয়। Unverified step-এর side effect আগেই ঘটতে পারে, তাই resume করার আগে current state দেখে নাও—action পুনরাবৃত্তি হওয়ার ঝুঁকি থাকে এবং approval gates বহাল থাকে। এই feature বিদ্যমান allow-listed tools-এর সীমার মধ্যে কাজ করে; এটি arbitrary shell command, যেকোনো website/app-এ unrestricted control, অথবা প্রতিটি external side effect-এর নিশ্চয়তাপূর্ণ verification নয়.

এই সংস্করণে তোমার দেওয়া তিনটি character image যুক্ত করা হয়েছে এবং সেগুলো `assets/characters/reference/`-এ মূল JPEG bytes অপরিবর্তিত রেখে রাখা হয়েছে।

## Voice reliability

Speech recognition-এর network operation ১৫ সেকেন্ডে সীমাবদ্ধ। Edge TTS-এর audio তৈরি ও playback-এরও সময়সীমা আছে; online speech service আটকে গেলে available থাকলে local `pyttsx3` fallback ব্যবহার করার চেষ্টা হবে। তবুও বাস্তব microphone, speaker ও Windows device-এ পরীক্ষা করা জরুরি।

## Character
- **LUNA:** বেগুনি চুলের full-body artwork
- **RUBY:** লাল চুলের full-body artwork
- **MAYA:** বাদামি চুলের square portrait

LUNA, RUBY ও MAYA-র ছোট ছবি শুধু reference thumbnail হিসেবে থাকবে। মূল dashboard-এর **OPEN REAL 3D AVATAR STUDIO** বোতাম চাপলে আলাদা browser window/tab-এ 3D character viewer খুলবে। সেখানে head, torso, upper/lower arms, thighs, lower legs এবং eyes আলাদা 3D mesh হিসেবে render হয়; idle movement, হাত নাড়ানো, knee/leg movement, blink এবং simulated speech mouth motion আছে। মূল 2D ছবিকে flat plane হিসেবে নড়ানো হচ্ছে না।

এটি সত্যিকারের 3D geometry-র prototype, কিন্তু procedural character-এর reference art-এর সঙ্গে 100% exact 3D likeness নয়। আরও বাস্তব model থাকলে **IMPORT RIGGED .GLB** চাপ দিয়ে নিজের PC-র `.glb` file বেছে নিতে পারবে। File browser-এর ভেতরেই load হয়, server-এ upload হয় না। GLB-তে idle/wave/talk animation clip থাকলে নাম দেখে সেগুলো চালানোর চেষ্টা করবে; clip না থাকলে Studio সেই motion নিজে তৈরি করতে পারবে না। Natural walking, realistic hair/cloth physics, custom model creation, proper facial rig ও phoneme-level lip-sync এখনও বাকি। Maya-র source শুধু portrait হওয়ায় সেখান থেকে hidden full-body anatomy পাওয়া যায় না। Three.js CDN থেকে load হয়, তাই 3D preview-এর জন্য internet ও WebGL-compatible browser লাগবে। অসম্পূর্ণ feature-গুলোর বিস্তারিত `FEATURE_STATUS.md`-এ আছে। Character-এর 2D art থেকে 3D model, rig, animation clip তৈরি ও import করার ধাপগুলোর জন্য [3D_CHARACTER_PIPELINE_BN.md](3D_CHARACTER_PIPELINE_BN.md) দেখো।

## ORVIX AI Logo ও Responsive Design

- `assets/branding/jarvis-mark.svg` হলো ORVIX AI app icon-এর source; `jarvis-wordmark.svg` হলো official wordmark। Legacy file name compatibility-এর জন্য রাখা হয়েছে।
- `install.bat` এখন app logo ও multi-size Windows `.ico` তৈরি করে এবং Desktop shortcut-এ সেট করে।
- Desktop window ছোট করলে ডান পাশের utility panel লুকিয়ে যায়, আর top navigation-এর decorative label collapse হয়—ফলে মূল task workspace বড় জায়গা পায়।
- Minimum window size 820×560; এটি এখনো desktop software। Android/phone installer পরে আলাদা phase-এ হবে।

## Android/iOS Mobile Status

Android/iOS-এর প্রাথমিক Flutter client `mobile/`-এ আছে। এটি এখন chat ও secure provider settings সমর্থন করার ভিত্তি; Windows desktop agent-এর সব feature-এর সমতুল্য নয়, এবং signed APK/AAB বা iOS App Store build এখনো release করা হয়নি। বিস্তারিত `mobile/README.md` ও `FEATURE_STATUS.md`-এ আছে।

## Source install (যদি installer ব্যবহার না করো)
1. Windows 11-এ Python 3.12.x 64-bit ইনস্টল করো: https://www.python.org/downloads/release/python-31210/
2. ZIP Extract করো অথবা repository clone করো।
3. `Zobaerio-Jarvis-AI/` folder খুলে `install.bat` double-click করো।
4. Install সফল হলে `run.bat` double-click করো।
5. বাম পাশে LUNA, RUBY অথবা MAYA সিলেক্ট করো।
6. Local AI-এর জন্য Ollama ইনস্টল করে PowerShell-এ চালাও: `ollama pull qwen2.5:3b`। Settings-এ Base URL `http://localhost:11434/v1`, model `qwen2.5:3b` দাও।

## নিরাপত্তা ও সীমাবদ্ধতা

App-এর sensitive action-এর জন্য approval gate আছে। এটি প্রতিটি app বা website-এ unrestricted control দেয় না। Task history ও queued command স্থানীয় JSON file-এ সংরক্ষিত হয়; sensitive তথ্য command হিসেবে দিও না। সব implemented এবং unfinished feature দেখতে `FEATURE_STATUS.md` পড়ো।
