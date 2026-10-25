# বাস্তবসম্মত 3D Character বানানোর পথ — বাংলা

এই guide-টি J.A.R.V.I.S v1.2.3-এর **IMPORT RIGGED .GLB** feature-এর জন্য। Built-in LUNA/RUBY/MAYA এখনও stylized procedural mesh; এই pipeline ব্যবহার করলে supplied artwork-এর আরও কাছাকাছি textured 3D character বানিয়ে সেটি Studio-তে import করতে পারবে।

## কোন ছবিটি ব্যবহার করবে

- **LUNA** এবং **RUBY**: source reference-এ পুরো শরীর দেখা যায়, তাই image-to-3D test শুরু করতে এই দুটির একটি বেছে নাও।
- **MAYA**: source image শুধু portrait; পা, full outfit, পিছনের দিক ও body proportions ছবিতে নেই। একই character-এর full-body front reference বানানো/জোগাড় করা ছাড়া পুরো শরীর সঠিকভাবে পুনর্গঠন সম্ভব নয়।

একটি 2D image থেকে model generator-কে দেখা যায় না এমন পেছনের/পাশের অংশ অনুমান করতে হয়। ফলে “100% same” নিশ্চয়তা নেই; generation-এর পর face, hair, hands, outfit ও back view পরীক্ষা করে দরকার হলে Blender-এ edit করতে হবে।

## ধাপ ১ — Image-to-3D model তৈরি করো

Official options:
- Meshy Image-to-3D: https://www.meshy.ai/features/image-to-3d
- Meshy API docs: https://docs.meshy.ai/en/api/image-to-3d
- Tripo 3D API docs: https://docs.tripo3d.ai/

1. যে character-টি তৈরি করবে সেটির reference image upload করো। পরিষ্কার background, পুরো body frame-এর মধ্যে, এবং high-resolution image ব্যবহার করো।
2. Textured model generation বেছে নাও এবং output format হিসেবে **GLB** নির্বাচন করো।
3. Generation-এর credits/cost ও privacy policy আগে দেখো। Image cloud service-এ upload হবে; generated 3D model-এর quality/reference match নিজে inspect করবে।
4. Model download করে locally রাখো। API key থাকলে কখনো GitHub, README বা chat-এ paste করবে না।

Meshy-এর official page image-to-3D model export formats-এর মধ্যে GLB দেখায়; এর API-তেও image-to-3D task তৈরি করা যায়। API/credit pricing বদলাতে পারে, তাই প্রতিবার official page-এ বর্তমান তথ্য দেখবে।

## ধাপ ২ — model-কে rig ও animation দাও

Static GLB-তে skeleton/animation না থাকলে Studio সেটিকে নিজে থেকে হাঁটাতে বা হাত নাড়াতে পারবে না। Rigging/animation-এর জন্য:

- Tripo Rigging: https://developers.tripo3d.com/en/models/rig — model rig করে rigged GLB/FBX output দেওয়ার workflow।
- Adobe Mixamo: https://helpx.adobe.com/ae_en/creative-cloud/help/mixamo-rigging-animation.html — character upload, auto-rig এবং animation apply করার official guide। Mixamo upload-এর supported format FBX, OBJ বা ZIP; GLB file হলে আগে Blender-এ import করে FBX export করতে হতে পারে।

Rigging-এর পর অন্তত একটি **idle/stand** clip এবং একটি **wave/hello/gesture** clip যোগ করো। Browser Studio imported clips-এর নামের মধ্যে idle, rest, stand, wave, hello, gesture, talk, speak ইত্যাদি খোঁজে। Clip-এর নাম না মিললে Studio সেটি automatic ভাবে চিনতে নাও পারে। Blender export করার সময় animation clips ও texture ঠিকমতো যুক্ত আছে কি না পরীক্ষা করবে।

> Talking clip ও আসল lip-sync এক নয়। Production lip-sync-এর জন্য face blendshapes/visemes এবং audio অনুযায়ী phoneme timing লাগবে; এই feature এখনও built-in নয়।

## ধাপ ৩ — J.A.R.V.I.S-এ import করো

1. J.A.R.V.I.S চালিয়ে LUNA, RUBY অথবা MAYA profile বেছে নাও।
2. **OPEN REAL 3D AVATAR STUDIO** চাপো।
3. **IMPORT RIGGED .GLB** চাপো এবং তোমার তৈরি .glb বেছে নাও।
4. Studio local browser-এ model read করবে; GLB file নিজে থেকে কোনো web server-এ upload করে না।
5. Orbit/zoom দিয়ে face, hands, clothes, side/back view দেখে quality যাচাই করো। Wave control শুধু matching wave/hello/gesture clip থাকলে চলবে; Speak Greeting-এর জন্য matching talk/speak clip থাকলে সেটি চলবে।

## বর্তমান সীমা

- Built-in character models reference art-এর exact 3D conversion নয়।
- Image generation, rigging এবং animation file তৈরি এখনো external workflow; J.A.R.V.I.S-এর ভিতরে one-click automatic generation নেই।
- Maya-র provided portrait থেকে full-body character automatically পাওয়া যায় না।
- Natural walking, hair/cloth physics, finger articulation, expressive facial rig এবং phoneme-level lip-sync এখনো production-ready নয়।
- Import viewer-এর জন্য internet/WebGL দরকার, কারণ Three.js module CDN থেকে লোড হয়।

See also FEATURE_STATUS.md for the complete implemented/partial/missing feature inventory.
