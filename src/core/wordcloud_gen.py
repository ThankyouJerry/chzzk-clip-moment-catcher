"""
WordCloud Generator with Cross-Platform Font Support
"""
import platform
from pathlib import Path
from wordcloud import WordCloud
from typing import Callable, Optional

from core.errors import TaskCancelled
from core.file_io import atomic_save


class WordCloudGenerator:
    """Generates wordcloud from text data"""
    
    def __init__(self):
        self.wordcloud: Optional[WordCloud] = None

    def reset(self) -> None:
        """Discard the image generated for the previous source."""
        self.wordcloud = None
    
    def get_korean_font(self) -> str:
        """Get Korean font path based on platform"""
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
            if Path(font_path).exists():
                return font_path
            # Fallback
            return '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
        
        elif system == 'Windows':
            # Try common Korean fonts on Windows
            fonts = [
                'C:\\Windows\\Fonts\\malgun.ttf',  # 맑은 고딕
                'C:\\Windows\\Fonts\\gulim.ttc',   # 굴림
                'C:\\Windows\\Fonts\\batang.ttc',  # 바탕
            ]
            for font in fonts:
                if Path(font).exists():
                    return font
            # Fallback to Arial Unicode
            return 'C:\\Windows\\Fonts\\arial.ttf'
        
        else:  # Linux
            fonts = [
                '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',
            ]
            for font in fonts:
                if Path(font).exists():
                    return font
            # Fallback
            return None
    
    def generate(
        self,
        text: str,
        width: int = 800,
        height: int = 400,
        max_words: int = 100,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """
        Generate wordcloud from text
        
        Args:
            text: Input text
            width: Image width
            height: Image height
            max_words: Maximum number of words
            
        Returns:
            True if successful
        """
        if not text.strip():
            return False
        if cancel_check is not None and cancel_check():
            raise TaskCancelled("작업이 취소되었습니다.")
        
        font_path = self.get_korean_font()
        
        # Commit the image only after generation and cancellation checks succeed.
        generated = WordCloud(
            font_path=font_path,
            width=width,
            height=height,
            background_color='white',
            colormap='viridis',
            max_words=max_words,
            relative_scaling=0.5,
            min_font_size=10
        ).generate(text)
        if cancel_check is not None and cancel_check():
            raise TaskCancelled("작업이 취소되었습니다.")
        self.wordcloud = generated
        return True
    
    def save(self, output_path: str, *, image=None) -> bool:
        """
        Save wordcloud to file
        
        Args:
            output_path: Output file path
            
        Returns:
            True if successful
        """
        if self.wordcloud is None and image is None:
            return False

        if image is not None:
            writer = lambda temporary: image.save(temporary, format="PNG")
        else:
            writer = lambda temporary: self.wordcloud.to_file(str(temporary))
        atomic_save(
            output_path,
            writer,
        )
        return True
    
    def get_wordcloud(self) -> Optional[WordCloud]:
        """Get generated wordcloud object"""
        return self.wordcloud
