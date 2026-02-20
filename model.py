import sounddevice as sd
import numpy as np
import threading
import queue
import time
import logging
import traceback
import os
from faster_whisper import WhisperModel
import torch 

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContinuousTranscriber:
    def __init__(self, target_language='en'):
        self.device = "cpu"
        logger.info(f"Using device: {self.device}")
        
        self.sample_rate = 16000
        self.buffer = queue.Queue()
        self.running = False
        self.buffer_duration = 2  # seconds
        self.samples_per_chunk = int(self.sample_rate * self.buffer_duration)
        self.callback_function = None
        self.min_audio_level = 0.01
        self.translation_available = True  # Flag to track if translation works
        
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
        logger.info(f"Target language set to: {self.target_language}")
        
        # Initialize Faster-Whisper model
        logger.info("Loading Faster-Whisper model...")
        try:
            model_size = "tiny"
            compute_type = "int8"
            
            # Use specific cache directory
            cache_dir = os.path.expanduser("~/.cache/faster-whisper")
            os.makedirs(cache_dir, exist_ok=True)
            
            self.whisper_model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=1,
                download_root=cache_dir
            )
            logger.info(f"Faster-Whisper model '{model_size}' loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Faster-Whisper model: {str(e)}")
            raise

        # Initialize translation if needed
        self.translation_model = None
        self.translation_tokenizer = None
        
        if self.target_language != 'en':
            self._setup_translation()

        self.processing_thread = None
        self.stream = None

    def _setup_translation(self):
        """Setup translation model with proper error handling and dependency checking"""
        try:
            # Check for required packages
            import importlib.util
            
            # Check for sentencepiece
            if importlib.util.find_spec("sentencepiece") is None:
                logger.error("❌ sentencepiece not installed! Translation will not work.")
                logger.error("Please install: pip install sentencepiece")
                self.translation_available = False
                return
            
            # Check for protobuf
            if importlib.util.find_spec("google.protobuf") is None:
                logger.error("❌ protobuf not installed! Translation may fail.")
                logger.error("Please install: pip install protobuf")
            
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
            logger.info(f"Loading translation model: {model_name}")
            
            # Load models on CPU with explicit error handling
            try:
                self.translation_model = MarianMTModel.from_pretrained(model_name)
                self.translation_tokenizer = MarianTokenizer.from_pretrained(model_name)
                logger.info("✅ Translation model loaded successfully")
                self.translation_available = True
            except Exception as e:
                logger.error(f"Failed to load translation model: {str(e)}")
                if "sentencepiece" in str(e).lower():
                    logger.error("💡 FIX: Run 'pip install sentencepiece'")
                self.translation_available = False
                self.translation_model = None
                
        except ImportError as e:
            logger.error(f"Import error: {e}")
            logger.error("Required packages missing. Run:")
            logger.error("pip install transformers sentencepiece protobuf torch")
            self.translation_available = False
            self.translation_model = None
        except Exception as e:
            logger.error(f"Unexpected error loading translation: {str(e)}")
            logger.error(traceback.format_exc())
            self.translation_available = False
            self.translation_model = None

    def _validate_language(self, language_code):
        """Validate language code and return normalized version"""
        if language_code in self.available_languages.values():
            return language_code
        
        for name, code in self.available_languages.items():
            if language_code.lower() == name.lower():
                return code
        
        logger.warning(f"Invalid language code '{language_code}', defaulting to English")
        return 'en'

    def _get_language_name(self, language_code):
        """Get full language name from code"""
        try:
            return next(name for name, code in self.available_languages.items()
                       if code == language_code)
        except StopIteration:
            return language_code

    def _translate_text(self, text):
        """Translate text with robust error handling"""
        if not text or self.target_language == 'en':
            return None
            
        if not self.translation_available:
            logger.warning("Translation unavailable - missing dependencies")
            return None
            
        if not self.translation_model or not self.translation_tokenizer:
            logger.warning("Translation model not loaded")
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
            
            with torch.no_grad():
                translated_ids = self.translation_model.generate(
                    **inputs,
                    max_length=512,
                    num_beams=2,
                    length_penalty=0.6,
                    early_stopping=True,
                    no_repeat_ngram_size=3
                )
            
            translation = self.translation_tokenizer.decode(
                translated_ids[0], 
                skip_special_tokens=True
            )
            
            if translation:
                logger.debug(f"✅ Translation successful: '{text[:30]}...' → '{translation[:30]}...'")
            return translation
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            if "sentencepiece" in str(e).lower():
                logger.error("💡 Missing sentencepiece! Run: pip install sentencepiece")
                self.translation_available = False
            return None

    def process_audio_chunk(self, audio_data):
        """Process audio chunk with Faster-Whisper"""
        try:
            # Check audio level
            audio_level = np.max(np.abs(audio_data))
            if audio_level < self.min_audio_level:
                logger.debug(f"Audio level too low: {audio_level}")
                return None, None
            
            # Normalize audio to [-1, 1] range
            audio_data = audio_data.astype(np.float32)
            if audio_level > 0:
                audio_data = audio_data / audio_level
            
            # Transcribe with Faster-Whisper
            logger.debug("Starting transcription with Faster-Whisper")
            
            segments, info = self.whisper_model.transcribe(
                audio_data,
                language="en",
                task="transcribe",
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=100,
                    speech_pad_ms=400
                ),
                without_timestamps=True,
                condition_on_previous_text=False
            )
            
            # Collect all segments
            transcription_parts = []
            for segment in segments:
                transcription_parts.append(segment.text)
                logger.debug(f"Segment: {segment.text[:50]}...")
            
            transcription = " ".join(transcription_parts).strip()
            
            if not transcription:
                logger.debug("No transcription generated")
                return None, None
            
            logger.info(f"✅ Transcription: {transcription[:100]}...")
            
            # Translate if needed
            translation = None
            if self.target_language != 'en':
                translation = self._translate_text(transcription)
                if translation:
                    logger.info(f"✅ Translation: {translation[:100]}...")
                else:
                    logger.warning("❌ Translation failed")
            
            return transcription, translation
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None

    def set_callback(self, callback):
        self.callback_function = callback
        logger.info("Callback function set")
    
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        
        try:
            audio_data = indata.mean(axis=1) if indata.ndim > 1 else indata.flatten()
            self.buffer.put(audio_data.copy())
        except Exception as e:
            logger.error(f"Error in audio callback: {str(e)}")
    
    def process_audio(self):
        """Main audio processing loop"""
        logger.info("Starting audio processing loop")
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
                        
                        if time.time() - start_time > self.buffer_duration * 1.5:
                            logger.debug("Buffer collection timeout - no speech detected")
                            break
                            
                    except queue.Empty:
                        continue
                
                if not self.running:
                    break
                    
                if not audio_chunks:
                    continue
                
                audio_data = np.concatenate(audio_chunks)
                if len(audio_data) > self.samples_per_chunk:
                    audio_data = audio_data[:self.samples_per_chunk]
                
                transcription, translation = self.process_audio_chunk(audio_data)
                
                if transcription and self.callback_function:
                    self.callback_function(transcription, translation)
                    
                    lang_name = self._get_language_name(self.target_language)
                    if translation:
                        logger.info(f"📤 Sending: {lang_name} translation")
                    else:
                        logger.info(f"📤 Sending: English transcription")
                    
                    last_transcription_time = time.time()
                elif time.time() - last_transcription_time > 5.0:
                    if self.callback_function:
                        self.callback_function("", "")
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(0.1)
    
    def start_transcription(self):
        """Start the transcription process"""
        if self.running:
            logger.warning("Transcription already running")
            return
        
        self.running = True
        logger.info("Starting transcription")
        
        try:
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * 0.1),
                dtype='float32'
            )
            self.stream.start()
            logger.info("Audio stream started")
            
            self.processing_thread = threading.Thread(target=self.process_audio)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("Processing thread started")
            
        except Exception as e:
            self.running = False
            logger.error(f"Error starting transcription: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def stop_transcription(self):
        """Stop the transcription process"""
        logger.info("Stopping transcription")
        self.running = False
        
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logger.info("Audio stream stopped")
            
            if self.processing_thread:
                self.processing_thread.join(timeout=2.0)
                self.processing_thread = None
            
            while not self.buffer.empty():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    break
            
            logger.info("Transcription stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping transcription: {str(e)}")
            logger.error(traceback.format_exc())
    
    def get_supported_languages(self):
        """Return dictionary of supported languages"""
        return self.available_languages