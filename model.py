import sounddevice as sd
import numpy as np
import threading
import queue
import time
import logging
import traceback
from faster_whisper import WhisperModel

import torch 
# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ContinuousTranscriber:
    def __init__(self, target_language='en'):
        self.device = "cpu"
        logging.info(f"Using device: {self.device}")
        
        self.sample_rate = 16000
        self.buffer = queue.Queue()
        self.running = False
        self.buffer_duration = 2  # seconds
        self.samples_per_chunk = int(self.sample_rate * self.buffer_duration)
        self.callback_function = None
        self.min_audio_level = 0.01
        
        # Language mapping for translation
        self.available_languages = {
            'English': 'en',
            'Spanish': 'es',
            'French': 'fr',
            'Italian': 'it',
            'Portuguese': 'pt',
            'Romanian': 'ro',
            'Catalan': 'ca',
            'German': 'de',
            'Dutch': 'nl',
            'Russian': 'ru',
            'Japanese': 'ja',
            'Chinese': 'zh'
        }
        
        # Validate and set target language
        self.target_language = self._validate_language(target_language)
        logging.info(f"Target language set to: {self.target_language}")
        
        # Initialize Faster-Whisper model
        logging.info("Loading Faster-Whisper model...")
        try:
            # Choose model size based on available resources
            model_size = "tiny"  # Can be "tiny", "base", "small", "medium", "large-v3"
            
            # For CPU with limited RAM, use int8
            compute_type = "int8"
            
            self.whisper_model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=1,
                download_root=None  # Optional: specify a cache directory
            )
            logging.info(f"Faster-Whisper model '{model_size}' loaded successfully with {compute_type}")
        except Exception as e:
            logging.error(f"Error loading Faster-Whisper model: {str(e)}")
            raise

        # Initialize translation if needed
        self.translation_model = None
        self.translation_tokenizer = None
        
        if self.target_language != 'en':
            try:
                from transformers import MarianMTModel, MarianTokenizer
                
                # Map target language to appropriate translation model
                translation_models = {
                    'es': "Helsinki-NLP/opus-mt-en-es",
                    'fr': "Helsinki-NLP/opus-mt-en-fr",
                    'de': "Helsinki-NLP/opus-mt-en-de",
                    'nl': "Helsinki-NLP/opus-mt-en-nl",
                    'it': "Helsinki-NLP/opus-mt-en-it",
                    'pt': "Helsinki-NLP/opus-mt-en-pt",
                    'ro': "Helsinki-NLP/opus-mt-en-ro",
                    'ru': "Helsinki-NLP/opus-mt-en-ru",
                    'ja': "Helsinki-NLP/opus-mt-en-ja",
                    'zh': "Helsinki-NLP/opus-mt-en-zh"
                }
                
                model_name = translation_models.get(self.target_language, "Helsinki-NLP/opus-mt-en-ROMANCE")
                logging.info(f"Loading translation model: {model_name}")
                
                # Load models on CPU
                self.translation_model = MarianMTModel.from_pretrained(model_name)
                self.translation_tokenizer = MarianTokenizer.from_pretrained(model_name)
                
                logging.info("Translation model loaded successfully on CPU")
            except Exception as e:
                logging.error(f"Error loading translation model: {str(e)}")
                self.translation_model = None

        self.processing_thread = None
        self.stream = None

    def _validate_language(self, language_code):
        """Validate language code and return normalized version"""
        # First check if it's a valid language code
        if language_code in self.available_languages.values():
            return language_code
        
        # Then check if it's a valid language name
        for name, code in self.available_languages.items():
            if language_code.lower() == name.lower():
                return code
        
        logging.warning(f"Invalid language code '{language_code}', defaulting to English")
        return 'en'

    def _get_language_name(self, language_code):
        """Get full language name from code"""
        try:
            return next(name for name, code in self.available_languages.items()
                       if code == language_code)
        except StopIteration:
            return language_code

    def _translate_text(self, text):
        """Translate text using MarianMT model on CPU"""
        if not text or self.target_language == 'en' or not self.translation_model:
            return None
            
        try:
            # Tokenize and translate on CPU
            inputs = self.translation_tokenizer(
                text, 
                return_tensors="pt", 
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # No need to move to GPU - keep on CPU
            
            with torch.no_grad():
                translated_ids = self.translation_model.generate(
                    **inputs,
                    max_length=512,
                    num_beams=2,  # Reduced for CPU performance
                    length_penalty=0.6,
                    early_stopping=True,
                    no_repeat_ngram_size=3
                )
            
            # Decode translation
            translation = self.translation_tokenizer.decode(
                translated_ids[0], 
                skip_special_tokens=True
            )
            return translation
            
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            return None

    def process_audio_chunk(self, audio_data):
        """Process audio chunk with Faster-Whisper"""
        try:
            # Check audio level
            audio_level = np.max(np.abs(audio_data))
            if audio_level < self.min_audio_level:
                logging.debug(f"Audio level too low: {audio_level}")
                return None, None
            
            # Normalize audio to [-1, 1] range (Faster-Whisper expects this)
            audio_data = audio_data.astype(np.float32)
            if audio_level > 0:
                audio_data = audio_data / audio_level
            
            # Transcribe with Faster-Whisper
            logging.debug("Starting transcription with Faster-Whisper")
            
            segments, info = self.whisper_model.transcribe(
                audio_data,
                language="en",  # Specify language for better performance
                task="transcribe",
                beam_size=1,  # Lower for speed, higher for accuracy
                best_of=1,
                temperature=0.0,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=100,
                    speech_pad_ms=400
                ),
                without_timestamps=True,  # We don't need timestamps
                condition_on_previous_text=False,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            # Collect all segments
            transcription_parts = []
            for segment in segments:
                transcription_parts.append(segment.text)
                logging.debug(f"Segment {segment.start:.2f}s - {segment.end:.2f}s: {segment.text}")
            
            transcription = " ".join(transcription_parts).strip()
            
            if not transcription:
                logging.debug("No transcription generated")
                return None, None
            
            # Translate if needed
            translation = None
            if self.target_language != 'en' and self.translation_model:
                translation = self._translate_text(transcription)
            
            return transcription, translation
            
        except Exception as e:
            logging.error(f"Error processing audio chunk: {str(e)}")
            logging.error(traceback.format_exc())
            return None, None

    def set_callback(self, callback):
        self.callback_function = callback
        logging.info("Callback function set")
    
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logging.warning(f"Audio status: {status}")
        
        try:
            # Convert to mono if stereo
            audio_data = indata.mean(axis=1) if indata.ndim > 1 else indata.flatten()
            self.buffer.put(audio_data.copy())
        except Exception as e:
            logging.error(f"Error in audio callback: {str(e)}")
    
    def process_audio(self):
        """Main audio processing loop"""
        logging.info("Starting audio processing loop")
        last_transcription_time = time.time()
        
        while self.running:
            try:
                # Collect audio chunks
                audio_chunks = []
                current_size = 0
                start_time = time.time()
                
                while current_size < self.samples_per_chunk and self.running:
                    try:
                        chunk = self.buffer.get(timeout=0.1)
                        audio_chunks.append(chunk)
                        current_size += len(chunk)
                        
                        # Prevent infinite loop if audio is too quiet
                        if time.time() - start_time > self.buffer_duration * 1.5:
                            logging.debug("Buffer collection timeout - no speech detected")
                            break
                            
                    except queue.Empty:
                        continue
                
                if not self.running:
                    break
                    
                if not audio_chunks:
                    continue
                
                # Concatenate audio chunks
                audio_data = np.concatenate(audio_chunks)
                if len(audio_data) > self.samples_per_chunk:
                    audio_data = audio_data[:self.samples_per_chunk]
                
                # Process the audio chunk
                transcription, translation = self.process_audio_chunk(audio_data)
                
                # Send to callback if available
                if transcription and self.callback_function:
                    self.callback_function(transcription, translation)
                    
                    lang_name = self._get_language_name(self.target_language)
                    logging.info(f"English: {transcription}")
                    if translation:
                        logging.info(f"Translation ({lang_name}): {translation}")
                    
                    last_transcription_time = time.time()
                elif time.time() - last_transcription_time > 5.0:
                    # Send keepalive if no speech detected
                    if self.callback_function:
                        self.callback_function("", "")
                
            except Exception as e:
                logging.error(f"Error in audio processing loop: {str(e)}")
                logging.error(traceback.format_exc())
                time.sleep(0.1)
    
    def start_transcription(self):
        """Start the transcription process"""
        if self.running:
            logging.warning("Transcription already running")
            return
        
        self.running = True
        logging.info("Starting transcription")
        
        try:
            # Start audio stream
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
                dtype='float32'  # Use float32 for better precision
            )
            self.stream.start()
            logging.info("Audio stream started")
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self.process_audio)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logging.info("Processing thread started")
            
        except Exception as e:
            self.running = False
            logging.error(f"Error starting transcription: {str(e)}")
            logging.error(traceback.format_exc())
            raise
    
    def stop_transcription(self):
        """Stop the transcription process"""
        logging.info("Stopping transcription")
        self.running = False
        
        try:
            # Stop audio stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logging.info("Audio stream stopped")
            
            # Wait for processing thread to finish
            if self.processing_thread:
                self.processing_thread.join(timeout=2.0)
                if self.processing_thread.is_alive():
                    logging.warning("Processing thread did not stop cleanly")
                self.processing_thread = None
            
            # Clear buffer
            while not self.buffer.empty():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    break
            
            logging.info("Transcription stopped successfully")
            
        except Exception as e:
            logging.error(f"Error stopping transcription: {str(e)}")
            logging.error(traceback.format_exc())
    
    def get_supported_languages(self):
        """Return dictionary of supported languages"""
        return self.available_languages