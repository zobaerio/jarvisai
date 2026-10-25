# J.A.R.V.I.S Desktop AI — বাংলা Setup Guide

এই সংস্করণে তোমার দেওয়া তিনটি character image যুক্ত করা হয়েছে এবং সেগুলো `assets/characters/reference/`-এ মূল JPEG bytes অপরিবর্তিত রেখে রাখা হয়েছে।

## Character
- **LUNA:** বেগুনি চুলের full-body artwork
- **RUBY:** লাল চুলের full-body artwork
- **MAYA:** বাদামি চুলের square portrait

অ্যাপে character-এর idle motion হিসেবে হালকা breathing scale, body sway, bob এবং একটি best-effort blink effect আছে। এটা এখনও real skeletal animation / 3D rig নয়। একটি স্থির ছবির বাইরে হাত-পা সত্যিকারের মতো পৃথকভাবে হাঁটানো, natural lip-sync, বা সম্পূর্ণ মুখভঙ্গি করতে হলে rigged model বা animated frames দরকার। MAYA-র দেওয়া ছবিতে পুরো body নেই, তাই সেটির পা animate করা যায় না যতক্ষণ না অন্য body asset দেওয়া হচ্ছে।

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

## GitHub-এ পুরো project upload করতে

এই ChatGPT session-এর GitHub connector local ZIP attachment-কে সরাসরি Git binary file হিসেবে নিতে পারে না। তাই source ও character image অক্ষত রেখে upload করার জন্য `push_to_github.bat` যোগ করা হয়েছে।

1. ZIP Extract করে `Zobaerio-Jarvis-AI` folder খুলবে।
2. Git for Windows না থাকলে https://git-scm.com/download/win থেকে install করবে।
3. `push_to_github.bat`-এ double-click করবে এবং GitHub sign-in চাইলে অনুমতি দেবে।
4. Script repository clone করে `upload-jarvis-desktop-ai-...` branch-এ source/assets commit ও push করবে। এরপর Pull Request comparison page খুলবে; review করে PR তৈরি করবে।

এই script main branch-এ force push বা auto-merge করে না। Upload-এর আগে `.env`, API keys, passwords বা অন্য secret project folder-এ রেখো না।
