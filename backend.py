import soundcard as sc
import numpy as np
import soundfile as sf
from openai import OpenAI
import time
import threading
import tempfile
import os

api_key = 'sk-proj-XXXXX'
client = OpenAI(api_key=api_key)
model = 'gpt-4o'  # Set the model to the newest version
TARGET_LANGUAGE = "Portuguese"

class AudioProcessor:
    def __init__(self, sample_rate=16000, capture_duration=2, process_interval=30):
        self.sample_rate = sample_rate
        self.capture_duration = capture_duration
        self.process_interval = process_interval
        
        self.full_transcription = ""
        self.partial_transcription = ""
        self.full_translation = ""        
        self.previous_transcription = []
        self.previous_comments = ""
        self.is_recording = False
        self.translation_queue = []
        self.last_update_time = time.time()
        self.sentence_count = 0

    def amplify_audio(self, data, factor=1.5):
        amplified_data = data * factor
        amplified_data = np.clip(amplified_data, -1.0, 1.0)
        return amplified_data

    def save_to_file(self, recorded_audio):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        sf.write(temp_file.name, recorded_audio, self.sample_rate)
        temp_file.close()  # Ensure the file is properly closed
        return temp_file.name

    def transcribe_audio_with_whisper(self, file_path):
        start_time = time.time()
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        end_time = time.time()
        print(f"Whisper transcription took {end_time - start_time:.2f} seconds")
        return transcription

    def translate_text_to_portuguese(self, text, context):
        start_time = time.time()
        instructions = (
            f"Translate the following text to {TARGET_LANGUAGE}. Improve the translation by making it more coherent and natural:\n\n"
            f"Context:\n{context}\n\nText:\n{text}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ]
        )
        end_time = time.time()
        print(f"Translation to Portuguese took {end_time - start_time:.2f} seconds")
        return response.choices[0].message.content

    def generate_interview_response(self, full_transcription, previous_transcription, previous_comments):
        start_time = time.time()
        instructions = (
            "You are a helpful assistant. Your task is to suggest new, appropriate, and intelligent comments "
            "based on what is being talked about in a meeting. The comments should be in English and suitable for a professional context. "
            "You should only provide new insightful comments based on the most recent addition to the transcription. "
            "The comment should be short enough to be easily read during the meeting and help the participant with insightful things to mention on the meeting. "
            "Here are the details:\n\n"
            "Full transcription:\n"
            f"{full_transcription}\n\n"
            "Previous transcription:\n"
            f"{' '.join(previous_transcription[-3:])}\n\n"
            "Previous comments:\n"
            f"{previous_comments}\n"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": full_transcription}
            ]
        )
        end_time = time.time()
        print(f"Generating interview response took {end_time - start_time:.2f} seconds")
        return response.choices[0].message.content

    def process_audio(self, audio, transcription_full_callback, transcription_current_callback):
        # Convert to mono by averaging the two channels if stereo
        if audio.ndim == 2:
            audio = np.mean(audio, axis=1)
        print("Audio after mono conversion and amplification:", audio.shape, audio.dtype)  # Debugging output
        amplified_data = self.amplify_audio(audio, factor=3)
        audio_file = self.save_to_file(amplified_data)
        
        transcription = self.transcribe_audio_with_whisper(audio_file)
        os.remove(audio_file)  # Clean up temp file

        if not isinstance(transcription, str):
            transcription = str(transcription)  # Ensure transcription is a string

        self.partial_transcription += transcription + " "

        # Update the transcription area with partial results
        transcription_current_callback(self.partial_transcription)
        
        self.full_transcription += transcription + " "

        # Check if the transcription contains a meaningful segment
        if any(punct in transcription for punct in [".", "!", "?"]):            
            transcription_full_callback(self.full_transcription)
            # Increment sentence count and check time for update
            self.sentence_count += 1
            current_time = time.time()
            if self.sentence_count >= 2 or (current_time - self.last_update_time) >= 5:
                # Add the partial transcription to the translation queue with context
                context = ' '.join(self.full_transcription.split()[-50:])
                self.translation_queue.append((self.partial_transcription, context))
                # Reset sentence count and update time
                self.sentence_count = 0
                self.last_update_time = current_time
                self.partial_transcription = ""

        return transcription

    def capture_audio_loopback(self):
        default_speaker = sc.default_speaker()
        loopback_mic = sc.get_microphone(default_speaker.name, include_loopback=True)

        recorded_frames = []
        with loopback_mic.recorder(samplerate=self.sample_rate) as mic:
            data = mic.record(numframes=self.sample_rate * self.capture_duration)
            recorded_frames.append(data)

        recorded_audio = np.concatenate(recorded_frames, axis=0)
        return recorded_audio

    def handle_translation(self, translation_full_callback, translation_current_callback):
        while self.is_recording:
            if self.translation_queue:
                text_to_translate, context = self.translation_queue.pop(0)
                translated_text = self.translate_text_to_portuguese(text_to_translate, context)
                self.full_translation += translated_text + " "
                translation_full_callback(self.full_translation)
                translation_current_callback(translated_text)
            time.sleep(0.1)  # Short sleep to prevent busy waiting

    def handle_commenting(self, comments_callback):
        while self.is_recording:
            # Check if it's time to process the full transcription
            current_time = time.time()
            if current_time - self.last_process_time >= self.process_interval:
                # Generate insightful comments periodically
                insightful_comments = self.generate_interview_response(self.full_transcription, self.previous_transcription, self.previous_comments)
                self.previous_transcription.append(self.full_transcription)
                self.previous_comments += insightful_comments + " "

                # Update the comments
                comments_callback(insightful_comments)

                self.last_process_time = current_time

            time.sleep(1)  # Sleep for a short time to prevent busy waiting

    def main_loop(self, transcription_full_callback, transcription_current_callback, comments_callback, translation_full_callback, translation_current_callback):
        self.is_recording = True
        self.last_process_time = time.time()
        current_transcription = ""

        commenting_thread = threading.Thread(target=self.handle_commenting, args=(comments_callback,))
        translation_thread = threading.Thread(target=self.handle_translation, args=(translation_full_callback, translation_current_callback))
        commenting_thread.start()
        translation_thread.start()

        while self.is_recording:
            recorded_audio = self.capture_audio_loopback()
            print("Captured Audio:", recorded_audio.shape, recorded_audio.dtype)  # Debugging output
            new_transcription = self.process_audio(recorded_audio, transcription_full_callback, transcription_current_callback)
            if new_transcription:
                current_transcription += new_transcription + " "

        commenting_thread.join()  # Wait for commenting thread to finish when stopping recording
        translation_thread.join()  # Wait for translation thread to finish when stopping recording

    def stop_recording(self):
        self.is_recording = False
