# J.A.R.V.I.S Desktop AI — বাংলা Setup Guide

**সংস্করণ:** 1.4.0 — J.A.R.V.I.S Logo ও Responsive Agent UI

এই সংস্করণে তোমার দেওয়া তিনটি character image যুক্ত করা হয়েছে এবং সেগুলো `assets/characters/reference/`-এ মূল JPEG bytes অপরিবর্তিত রেখে রাখা হয়েছে।

## Character
- **LUNA:** বেগুনি চুলের full-body artwork
- **RUBY:** লাল চুলের full-body artwork
- **MAYA:** বাদামি চুলের square portrait

LUNA, RUBY ও MAYA-র ছোট ছবি শুধু reference thumbnail হিসেবে থাকবে। মূল dashboard-এর **OPEN REAL 3D AVATAR STUDIO** বোতাম চাপলে আলাদা browser window/tab-এ 3D character viewer খুলবে। সেখানে head, torso, upper/lower arms, thighs, lower legs এবং eyes আলাদা 3D mesh হিসেবে render হয়; idle movement, হাত নাড়ানো, knee/leg movement, blink এবং simulated speech mouth motion আছে। মূল 2D ছবিকে flat plane হিসেবে নড়ানো হচ্ছে না।

এটি সত্যিকারের 3D geometry-র prototype, কিন্তু procedural character-এর reference art-এর সঙ্গে 100% exact 3D likeness নয়। আরও বাস্তব model থাকলে **IMPORT RIGGED .GLB** চাপ দিয়ে নিজের PC-র `.glb` file বেছে নিতে পারবে। File browser-এর ভেতরেই load হয়, server-এ upload হয় না। GLB-তে idle/wave/talk animation clip থাকলে নাম দেখে সেগুলো চালানোর চেষ্টা করবে; clip না থাকলে Studio সেই motion নিজে তৈরি করতে পারবে না। Natural walking, realistic hair/cloth physics, custom model creation, proper facial rig ও phoneme-level lip-sync এখনও বাকি। Maya-র source শুধু portrait হওয়ায় সেখান থেকে hidden full-body anatomy পাওয়া যায় না। Three.js CDN থেকে load হয়, তাই 3D preview-এর জন্য internet ও WebGL-compatible browser লাগবে। অসম্পূর্ণ feature-গুলোর বিস্তারিত `FEATURE_STATUS.md`-এ আছে। Character-এর 2D art থেকে 3D model, rig, animation clip তৈরি ও import করার ধাপগুলোর জন্য [3D_CHARACTER_PIPELINE_BN.md](3D_CHARACTER_PIPELINE_BN.md) দেখো।

## Logo ও Responsive Design

- `assets/branding/jarvis-mark.svg` হলো app icon-এর source; `jarvis-wordmark.svg` হলো official wordmark।
- `install.bat` এখন app logo ও multi-size Windows `.ico` তৈরি করে এবং Desktop shortcut-এ সেট করে।
- Desktop window ছোট করলে ডান পাশের utility panel লুকিয়ে যায়, আর top navigation-এর decorative label collapse হয়—ফলে মূল task workspace বড় জায়গা পায়।
- Minimum window size 820×560; এটি এখনো desktop software। Android/phone installer পরে আলাদা phase-এ হবে।

## Install
1. Windows 11-এ Python 3.12.x 64-bit ইনস্টল করো: https://www.python.org/downloads/release/python-31210/
2. ZIP Extract করো অথবা repository clone করো।
3. `install.bat` double-click করো।
4. Install সফল হলে `run.bat` double-click করো।
5. বাম পাশে LUNA, RUBY অথবা MAYA সিলেক্ট করো।
6. Local AI-এর জন্য Ollama ইনস্টল করে PowerShell-এ চালাও: `ollama pull qwen2.5:3b`। Settings-এ Base URL `http://localhost:11434/v1`, model `qwen2.5:3b` দাও।

## নতুন: Task History ও Cancel Task

কোনো task চলার সময় নতুন command লিখে **QUEUE** চাপলে আগে অনুমতি চাইবে, তারপর সেটি FIFO queue-তে রাখবে। সক্রিয় task শেষ হলে armed queue-র পরের command চলবে। Restart-এর পর পুরোনো queued command নিজে থেকে চলবে না; **RUN QUEUED TASKS** চাপ দিয়ে আবার confirmation দিতে হবে।

ডান পাশের **ACTIVE TASKS** প্যানেল থেকে **CANCEL CURRENT TASK** চাপলে চলমান AI task-কে পরের tool action শুরু করা থেকে থামানোর অনুরোধ পাঠানো হয়। **TASK HISTORY**-তে শেষ ১০০টি task-এর command, status, সময়, result ও progress দেখা যায়। নির্বাচিত command আবার চালাতে **Retry Selected Task** চাপবে; আগে confirmation দেখাবে এবং নতুন task record তৈরি করবে। এটি বর্তমান AI settings দিয়ে আবার চালাবে। File/folder approval dialog-এও **Cancel Task** আছে।

এটি cooperative cancellation: model-এর network request ইতিমধ্যে আটকে থাকলে সেটি return না করা পর্যন্ত অপেক্ষা লাগতে পারে (read timeout ৪৫ সেকেন্ড), আর ইতিমধ্যে শুরু হওয়া external action স্বয়ংক্রিয়ভাবে undo করা যায় না। Cancel শনাক্ত হওয়ার পরে নতুন AI tool action শুরু করা হয় না।

History ও queued command এই PC-তে `%APPDATA%\Zobaerio\Jarvis\task_history.json`-এ JSON হিসেবে থাকে; এই feature সেটি encrypt করে না। Restart-এর পর saved queue চালাতে আলাদাভাবে confirmation দিতে হবে। Command হিসেবে password, API key বা secret দেবে না।

## গুরুত্বপূর্ণ
- Voice recognition / online neural speech-এর জন্য ইন্টারনেট লাগতে পারে; কিছু voice service-এ audio/text বাহ্যিক service-এ পাঠানো হতে পারে।
- File create/change করার আগে confirmation চাওয়ার নিরাপত্তা flow রাখা হয়েছে।
- arbitrary shell command স্বয়ংক্রিয়ভাবে চালানো যায় না।
- এটিকে production-ready বলার আগে নিজের Windows 11 PC-তে microphone, speaker, character selection এবং প্রতিটি command পরীক্ষা করবে।
