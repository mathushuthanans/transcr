<h1 align="center" style="border-bottom: none">
    <b>
        <a href = "https://sidhartha-s-935.github.io/Videocall_translation/">TalkIt Out<a>
    </b>
    <br>
    A Realtime Video Translation App <br>
</h1>

# [`Demo Video`](https://www.youtube.com/watch?v=sqxjYGoxZUg)

## Team Details

| Name        | Email                      |
| ----------- | -------------------------- |
| Sidhartha S | sidharthas935@gmail.com    |
| K Rajit     | rajitkumaran27@gmail.com   |
| Pavana K    | pavanakomaragiri@gmail.com |
| Malavika L  | malz311204@gmail.com       |
| Stephen Paul| stephenpaul4040@gmail.com  |

<div style="display: flex; flex-wrap: wrap;">
    <img src="https://cdn.discordapp.com/attachments/1155138775853322320/1218806742020788324/image.png?ex=6609013b&is=65f68c3b&hm=10ab87283e1a37539b8982f0af8a246ba28b28a340a979331ea6bd7fa23de837&" alt="Image 1" style="width: 30%; margin: 10px;">
    <img src="https://media.discordapp.net/attachments/1155138775853322320/1218806941107621898/image.png?ex=6609016b&is=65f68c6b&hm=e3fdec0b6363864afd80f0e9bc9196ff12ad9511d7ea4f0c7b74cd613a83a011&=&format=webp&quality=lossless&width=550&height=299" alt="Image 2" style="width: 30%; margin: 10px;"><br>
    <img src="https://media.discordapp.net/attachments/1155138775853322320/1218807435985420309/image.png?ex=660901e1&is=65f68ce1&hm=50d6c5ff776180b2c8d199f94cd5c295832f7bfe44b08c1df4336223b267e853&=&format=webp&quality=lossless" alt="Image 3" style="width: 30%; margin: 10px;">
    <img src="https://cdn.discordapp.com/attachments/1154800276075720836/1218841681839788082/image.png?ex=660921c5&is=65f6acc5&hm=8c1b8a975d5c6624f4fd4f7306a5eaa6ed7350ccd4a6305142ff50a8ae57fbfe&" alt="Image 4" style="width: 30%; margin: 10px;"><br>
    <img src="https://cdn.discordapp.com/attachments/1154800276075720836/1218841865965801517/image.png?ex=660921f1&is=65f6acf1&hm=d259266ca9188cf8a41365a99434cf9d3bdbb22aade4f34213fda51ebbf5bd1f&" alt="Image 5" style="width: 30%; margin: 10px;"><br>
    
</div>

## Problem statement

Language Barriers: People who speak different languages face challenges when trying to understand video content. Real-time translation and captioning can bridge this gap and make video content accessible to a global audience.

Inclusivity: In today's diverse world, inclusivity is crucial. Providing real-time translations and captions ensures that everyone, regardless of their language, can participate and benefit from video content.

Education and Learning: Students and educators often rely on video content for learning purposes. Real-time translations and captions can enhance the learning experience by ensuring that language barriers do not hinder comprehension.

Business and Communication: In a global business environment, effective communication is essential. Real-time translation and captioning can facilitate better communication between teams and clients from different linguistic backgrounds.

## About the project

The system will integrate speech recognition to capture spoken words during the video call and, for that case any video or audio file in the system or through our mic input, then use translation algorithms to convert the speech into the desired language in real-time. This solution aims to be user-friendly, providing an intuitive and uninterrupted experience for users.

## Technical implemntaion

- The app extracts the audio from the speaker in the call.
- transcribes the extracted audio in a the local host app.
- sent to the server of the Google translate where it is translated.
- The translated text is displayed as a caption in the caption window using PyQt5 model.
- The application also has a simple caching mechanism which store the transcribed and transalted output in the SQLite database
- checks the cache for availabilty if yes, then displayes the output from chache. If not , then sends the input to the Google Translate

  ![flowchart](https://cdn.discordapp.com/attachments/1155138775853322320/1218810800982986833/image.png?ex=66090503&is=65f69003&hm=4c7d82e51188065275960db38d7a1c3b382699a2d7ec7b6a0204c3fb561eeb82&)

## Techstacks used

`Python` , `Flask` , `SQLite` , `PyQt5` , `Google Translate API` , `HTML` , `TailwindCSS` , `JavaScript`

## How to run locally

- step 1 : clone the repo

- step 2 : install the dependencies

```
pip install -r requirements.txt
```

- step 3 : run the main app

```
python app.py
```

- step 4
  Select source and target language , start the translation and by default the application captures microphone audio for translation.

- step 5 : <b>To Translate Desktop audio</b>

  - `Win+R`

  - type ` mmsys.cpl` and run

  - Enable the Stereo Mix and set it as default communication device under the recording tab.

  - under Settings > System > Sounds : select Stereo Mix as input device

# What's next ?

The future improvements we aim to provide for this app is improved accuracy and
decreased latency using any other large language models that is far more accurate than Google translate.
We did plan on implementing WhisperAI API which has greater accuracy and decreased latency, but it needs a lot of computational power in order to run efficiently which hinders our approach on being user-friendly and easily accessible to a wide range of users
One of the major show stoppers is ambient noise and accent/dialect adaptation which we will try to improve with regular updates


