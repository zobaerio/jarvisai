# J.A.R.V.I.S Desktop AI — বাংলা Setup Guide

**সংস্করণ:** 1.6.2 — AI provider retry/backoff

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

## নতুন: Safe Recycle Bin Action

এখন Desktop, Documents বা Downloads থেকে একবারে একটি regular file Windows Recycle Bin-এ পাঠানো যাবে। Approval dialog-এ exact path, file size ও type দেখাবে। Directory, symbolic link, path traversal, missing file এবং approval চলাকালে file বদলে গেলে operation block হবে। এটি permanent delete নয়; Recycle Bin খালি করা না হলে এবং Windows অনুমতি দিলে ফাইল recover করা যাবে।

## নতুন: Duplicate File Finder

J.A.R.V.I.S Desktop, Documents, Downloads অথবা তিনটি folder-এই একই content-এর file খুঁজে বের করতে পারবে। আগে অনুমতি নেবে, তারপর একই size-এর candidate file-এর SHA-256 locally হিসাব করবে। সর্বোচ্চ ৫,০০০টি file entry scan, মোট ২৫৬ MiB পর্যন্ত hashing এবং ১০০ MiB-এর বড় individual file skip করা হবে। Hidden/generated folder, symbolic link ও hashing চলাকালে বদলে যাওয়া file বাদ থাকবে। AI conversation-এ কেবল matching path, size ও ছোট hash fingerprint যাবে—file content যাবে না। কোনো file পরিবর্তন বা delete হবে না; কোন copy মুছবে তা tool নিজে সিদ্ধান্ত নেবে।

## নতুন: নিরাপদ ZIP Archive তৈরি

J.A.R.V.I.S Desktop, Documents অথবা Downloads-এর একটি folder থেকে ১–১০০টি নির্বাচিত regular file নিয়ে সর্বোচ্চ ১০০ MiB uncompressed size-এর ZIP বানাতে পারবে। Confirmation dialog-এ archive-এর নাম এবং প্রতিটি selected file-এর নাম/size দেখাবে। Path traversal, symbolic link, directory, duplicate entry name, আগে থেকেই থাকা destination এবং approval-এর পর বদলে যাওয়া source file block হবে। Filesystem atomic no-overwrite publish সমর্থন না করলে operation ব্যর্থ হবে; existing archive overwrite করবে না। Original source file অপরিবর্তিত থাকবে।

## নতুন: App Restart-এর পর Task Recovery

অ্যাপ চালু হলে persistent Task History পরীক্ষা করবে। আগের process আর active না থাকা অবস্থায় কোনো task `running/cancelling` থাকলে সেটিকে timestamp ও recovery note-সহ `failed` করবে। Desktop/file action আংশিক সম্পন্ন হয়ে থাকতে পারে, তাই duplicate action ঠেকাতে নিজে থেকে আবার চালাবে না—retry করার আগে Task History দেখে নিতে হবে। Queued task queue-তেই থাকবে; recovery নিজে থেকে queued command চালু করে না। অন্য কোনো J.A.R.V.I.S process active মনে হলে তার task বদলাবে না।

## নতুন: নিরাপদ AI Error Handling

Provider-এর HTTP error body এখন সরাসরি chat-এ দেখানো হবে না—কারণ কোনো provider বা proxy ভুল করে private prompt, file excerpt বা credential ফিরিয়ে দিতে পারে। J.A.R.V.I.S সাধারণ HTTP status অনুযায়ী নিরাপদ ও কার্যকর পরামর্শ দেখাবে। পাশাপাশি invalid JSON, ভুল choices/message/tool-call structure এবং unexpected library/network error-কে neutral diagnostic-এ রূপান্তর করবে; raw error body বা exception message ইউজারকে দেখাবে না।

## নতুন: Secure API Endpoint ও Test Connection

Settings এখন API base URL যাচাই করে, URL-এর ভেতরে username/API key এবং query/fragment থাকলে block করে। Stored API key কোনো remote non-local endpoint-এ plain HTTP দিয়ে পাঠানো হবে না—remote provider-এর জন্য HTTPS ব্যবহার করবে; local Ollama/loopback address-এ HTTP চলতে পারে।

**Test Connection** শুধু `/models` endpoint-এ GET request পাঠায়। Chat prompt পাঠায় না বা answer generate করে না। Result endpoint পাওয়া যাচ্ছে কি না এবং configured model তালিকায় আছে কি না জানায়; এটি সব provider-এ chat completion/tool calling কাজ করবে তার নিশ্চয়তা নয়।

## নতুন: Settings Crash Recovery

Settings এখন unique temporary file-এ লিখে flush/fsync ও atomic replace-এর মাধ্যমে save হয়। সফল save-এর পর `settings.json.bak` recovery copy আপডেট হয়; primary settings file নষ্ট/পড়া না গেলে backup থেকে restore করার চেষ্টা করবে। এতে অসম্পূর্ণ JSON হওয়ার ঝুঁকি কমে, কিন্তু settings encrypt হয় না এবং এটি নিয়মিত device backup-এর বিকল্প নয়। API key আগের মতো Windows credential store-এ থাকে—এই JSON-এ নয়।

## নতুন: Task History ও Cancel Task

কোনো task চলার সময় নতুন command লিখে **QUEUE** চাপলে আগে অনুমতি চাইবে, তারপর সেটি FIFO queue-তে রাখবে। সক্রিয় task শেষ হলে armed queue-র পরের command চলবে। Restart-এর পর পুরোনো queued command নিজে থেকে চলবে না; **RUN QUEUED TASKS** চাপ দিয়ে আবার confirmation দিতে হবে।

ডান পাশের **ACTIVE TASKS** প্যানেল থেকে **CANCEL CURRENT TASK** চাপলে চলমান AI task-কে পরের tool action শুরু করা থেকে থামানোর অনুরোধ পাঠানো হয়। **TASK HISTORY**-তে শেষ ১০০টি task-এর command, status, সময়, result ও progress দেখা যায়। নির্বাচিত command আবার চালাতে **Retry Selected Task** চাপবে; আগে confirmation দেখাবে এবং নতুন task record তৈরি করবে। এটি বর্তমান AI settings দিয়ে আবার চালাবে। File/folder approval dialog-এও **Cancel Task** আছে।

এটি cooperative cancellation: model-এর network request ইতিমধ্যে আটকে থাকলে সেটি return না করা পর্যন্ত অপেক্ষা লাগতে পারে (read timeout ৪৫ সেকেন্ড), আর ইতিমধ্যে শুরু হওয়া external action স্বয়ংক্রিয়ভাবে undo করা যায় না। Cancel শনাক্ত হওয়ার পরে নতুন AI tool action শুরু করা হয় না।

History ও queued command এই PC-তে `%APPDATA%\Zobaerio\Jarvis\task_history.json`-এ JSON হিসেবে থাকে; এই feature সেটি encrypt করে না। Restart-এর পর saved queue চালাতে আলাদাভাবে confirmation দিতে হবে। Command হিসেবে password, API key বা secret দেবে না।

## নতুন: Text File পড়ার আগে অনুমতি

এখন J.A.R.V.I.S কোনো supported text/source file পড়ার আগে exact path ও file size দেখিয়ে confirmation নেবে। Dialog-এ স্পষ্টভাবে জানাবে যে file-এর লেখা AI conversation-এ যাবে এবং configured AI provider-এ পাঠানো হতে পারে। সর্বোচ্চ ১০০ KB-এর supported text file পড়তে পারবে; symbolic link, binary/null-byte file এবং confirmation চলাকালে বা পড়ার সময় বদলে যাওয়া file block করা হবে। অনুমতি না দিলে file-এর কোনো content AI-কে দেওয়া হবে না।

## নতুন: ফাইলের ভেতরের লেখা খোঁজা

Desktop, Documents, Downloads অথবা তিনটি folder-এই common text/source file-এর ভেতরে কোনো শব্দ বা phrase খুঁজতে পারবে। Search শুরু করার আগে confirmation dialog দেখাবে; সর্বোচ্চ ২০টি ছোট matching line AI conversation-এ যাবে এবং cloud provider ব্যবহার করলে সেখানেও পাঠানো হতে পারে—এ কথা স্পষ্টভাবে জানাবে। Hidden/ignored directory, symbolic link, binary file এবং ২৫৬ KB-এর বড় file বাদ থাকবে; সর্বোচ্চ ৫,০০০টি file scan হবে। কোনো file edit করবে না। এটি সীমিত text search, পুরো disk scan বা document-এর semantic quality verification নয়।

## নতুন: নিরাপদে নির্দিষ্ট ফাইল খোলা

Desktop, Documents অথবা Downloads থেকে নির্দিষ্ট document/data/image file default Windows application-এ খোলার আগে confirmation dialog-এ exact path, file type ও size দেখাবে। .exe file, script, symbolic link ও folder-এর বাইরে যাওয়ার path block করা হয়। Confirmation dialog খোলা থাকা অবস্থায় file বদলে গেলে operation থেমে যায়। Windows-কে file open করতে বলা হয়েছে—এটুকু নিশ্চিত করে; কোন app আসলে খুলেছে তা user-কে দেখে নিশ্চিত করতে হবে।

## নতুন: File Copy, Move ও Rename

J.A.R.V.I.S এখন Desktop, Documents এবং Downloads-এর ভেতরে একবারে একটি regular file copy, move অথবা rename করতে পারে। প্রতিটি operation-এর আগে approval dialog-এ source path, destination path, file size এবং কী কাজ হবে তা দেখাবে। আগে থেকে destination file থাকলে সেটি কখনো overwrite করবে না। Symbolic link এবং folder-এর বাইরে যাওয়ার path block করা হয়। Move/rename-এর ক্ষেত্রে আগে destination-এ copy সম্পন্ন করে, তারপর original সরানোর চেষ্টা করে; original সরানো না গেলে দুইটি copy-ই থাকবে এবং ফলাফলে partial state জানাবে। এই ফিচার file delete, পুরো folder copy বা এই তিনটি folder-এর বাইরে কাজ করে না।

## AI Agent-এর approved desktop control

AI Agent এখন visible app window-এর title list করতে পারে, নির্দিষ্ট window-তে text paste করতে পারে এবং অনুমোদিত editing/navigation shortcut পাঠাতে পারে। প্রতিটি paste/shortcut-এর আগে confirmation চাইবে এবং কোন window-তে কাজ হবে তা দেখাবে। Text paste করার পর Enter চাপবে না বা form submit করবে না। Enter, Alt+F4, Windows+R এবং arbitrary shortcut sequence blocked। Paste সত্যিই app-এ বসেছে কি না, নিজে থেকে যাচাই করতে পারে না—তাই app দেখে নিশ্চিত করবে। এছাড়া file/folder-এর অস্তিত্ব এবং নির্দিষ্ট window title মিলিয়ে basic verification করা যায়; কিন্তু document-এর content/quality বা পুরো external task সম্পূর্ণ হয়েছে কি না তা যাচাই করতে পারে না।

এটি এখনো full visual computer control নয়: screenshot/OCR দেখে app বুঝতে পারে না এবং যেকোনো জায়গায় mouse click করতে পারে না। সঠিক app/window খোলা রাখবে এবং প্রয়োজন হলে তার title-এর নির্দিষ্ট অংশ জানাবে।

## গুরুত্বপূর্ণ
- Voice recognition / online neural speech-এর জন্য ইন্টারনেট লাগতে পারে; কিছু voice service-এ audio/text বাহ্যিক service-এ পাঠানো হতে পারে।
- File create/copy/move/rename করার আগে নির্দিষ্ট action দেখিয়ে confirmation চাওয়ার নিরাপত্তা flow রাখা হয়েছে; destination overwrite করা হয় না।
- arbitrary shell command স্বয়ংক্রিয়ভাবে চালানো যায় না।
- এটিকে production-ready বলার আগে নিজের Windows 11 PC-তে microphone, speaker, character selection এবং প্রতিটি command পরীক্ষা করবে।
