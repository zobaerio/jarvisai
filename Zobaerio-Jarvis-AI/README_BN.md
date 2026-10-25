# J.A.R.V.I.S Desktop AI — বাংলা Setup Guide

এই সংস্করণে তোমার দেওয়া তিনটি character image যুক্ত করা হয়েছে এবং সেগুলো `assets/characters/reference/`-এ মূল JPEG bytes অপরিবর্তিত রেখে রাখা হয়েছে।

## Character
- **LUNA:** বেগুনি চুলের full-body artwork
- **RUBY:** লাল চুলের full-body artwork
- **MAYA:** বাদামি চুলের square portrait

LUNA, RUBY ও MAYA-র ছোট ছবি শুধু reference thumbnail হিসেবে থাকবে। মূল dashboard-এর **OPEN REAL 3D AVATAR STUDIO** বোতাম চাপলে আলাদা browser window/tab-এ 3D character viewer খুলবে। সেখানে head, torso, upper/lower arms, thighs, lower legs এবং eyes আলাদা 3D mesh হিসেবে render হয়; idle movement, হাত নাড়ানো, knee/leg movement, blink এবং simulated speech mouth motion আছে। মূল 2D ছবিকে flat plane হিসেবে নড়ানো হচ্ছে না।

এটি সত্যিকারের 3D geometry-র prototype, কিন্তু character-এর reference art-এর সঙ্গে 100% exact 3D likeness নয়। Natural walking, realistic hair/cloth physics, proper facial rig ও phoneme-level lip-sync এখনও বাকি; এর জন্য custom rigged GLB/VRM assets লাগবে। Maya-র source শুধু portrait হওয়ায় সেখান থেকে hidden full-body anatomy পাওয়া যায় না। Three.js CDN থেকে load হয়, তাই 3D preview-এর জন্য internet ও WebGL-compatible browser লাগবে। অসম্পূর্ণ feature-গুলোর বিস্তারিত `FEATURE_STATUS.md`-এ আছে।

## Install
1. Windows 11-এ Python 3.12.x 64-bit ইনস্টল করো: https://www.python.org/downloads/release/python-31210/
2. ZIP Extract করো অথবা repository clone করো।
3. `install.bat` double-click করো।
4. Install সফল হলে `run.bat` double-click করো।
5. বাম পাশে LUNA, RUBY অথবা MAYA সিলেক্ট করো।
6. Local AI-এর জন্য Ollama ইনস্টল করে PowerShell-এ চালাও: `ollama pull qwen2.5:3b`। Settings-এ Base URL `http://localhost:11434/v1`, model `qwen2.5:3b` দাও।

## গুরুত্বপূর্ণ
- Voice recognition / online neural speech-এর জন্য ইন্টারনেট লাগতে পারে; কিছু voice service-এ audio/text বাহ্যিক service-এ পাঠানো হতে পারে।
- File create/change করার আগে confirmation চাওয়ার নিরাপত্তা flow রাখা হয়েছে।
- arbitrary shell command স্বয়ংক্রিয়ভাবে চালানো যায় না।
- এটিকে production-ready বলার আগে নিজের Windows 11 PC-তে microphone, speaker, character selection এবং প্রতিটি command পরীক্ষা করবে।
