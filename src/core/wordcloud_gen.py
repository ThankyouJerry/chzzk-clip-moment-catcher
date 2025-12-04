"""
WordCloud Generator with Cross-Platform Font Support
"""
import platform
from pathlib import Path
from wordcloud import WordCloud
from typing import Optional


class WordCloudGenerator:
    """Generates wordcloud from text data"""
    
    def __init__(self):
        self.wordcloud: Optional[WordCloud] = None
    
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
    
    def generate(self, text: str, width: int = 800, height: int = 400, 
                 max_words: int = 100) -> bool:
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
        
        font_path = self.get_korean_font()
        
        # Create wordcloud
        self.wordcloud = WordCloud(
            font_path=font_path,
            width=width,
            height=height,
            background_color='white',
            colormap='viridis',
            max_words=max_words,
            relative_scaling=0.5,
            min_font_size=10
        ).generate(text)
        
        return True
    
    def save(self, output_path: str) -> bool:
        """
        Save wordcloud to file
        
        Args:
            output_path: Output file path
            
        Returns:
            True if successful
        """
        if self.wordcloud is None:
            return False
        
        self.wordcloud.to_file(output_path)
        return True
    
    def get_wordcloud(self) -> Optional[WordCloud]:
        """Get generated wordcloud object"""
        return self.wordcloud
