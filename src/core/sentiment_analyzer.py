"""
Sentiment Analyzer - Detects mood changes in chat streams
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re

from core.sentiment_lexicon import SENTIMENT_LEXICON, EMOTICON_SENTIMENT, get_all_keywords


class SentimentAnalyzer:
    """Analyzes sentiment and detects mood changes in chat data"""
    
    def __init__(self):
        self.sentiment_results: Optional[pd.DataFrame] = None
        self.mood_changes: List[Dict] = []
        
    def analyze_message(self, message: str) -> float:
        """
        Analyze sentiment of a single message
        
        Args:
            message: Chat message text
            
        Returns:
            Sentiment score (-1.0 to 1.0)
        """
        if pd.isna(message) or not message:
            return 0.0
        
        message = str(message).lower()
        score = 0.0
        matches = 0
        
        # Check all sentiment keywords
        all_keywords = get_all_keywords()
        for keyword, value in all_keywords.items():
            if keyword in message:
                score += value
                matches += 1
        
        # Normalize score
        if matches > 0:
            # Average score, but cap at -1 to 1
            score = score / matches
            score = max(-1.0, min(1.0, score))
        
        return score
    
    def calculate_message_frequency(self, df: pd.DataFrame, 
                                   interval_seconds: int) -> pd.DataFrame:
        """
        Calculate message frequency per time interval
        
        Args:
            df: DataFrame with 'seconds' column
            interval_seconds: Time interval in seconds
            
        Returns:
            DataFrame with time bins and message counts
        """
        max_seconds = df['seconds'].max()
        time_bins = list(range(0, max_seconds + interval_seconds, interval_seconds))
        
        df['time_bin'] = pd.cut(df['seconds'], bins=time_bins, labels=time_bins[:-1])
        frequency = df.groupby('time_bin').size().reset_index(name='frequency')
        frequency['time_seconds'] = frequency['time_bin'].astype(int)
        
        return frequency
    
    def analyze_timeline(self, df: pd.DataFrame, 
                        interval_minutes: float = 1.0) -> pd.DataFrame:
        """
        Analyze sentiment over time
        
        Args:
            df: DataFrame with chat messages (must have 'seconds' and 'clean_message' columns)
            interval_minutes: Time interval in minutes
            
        Returns:
            DataFrame with time, sentiment score, and message frequency
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        interval_seconds = int(interval_minutes * 60)
        
        # Calculate sentiment for each message
        df['sentiment'] = df['clean_message'].apply(self.analyze_message)
        
        # Group by time intervals
        max_seconds = df['seconds'].max()
        time_bins = list(range(0, max_seconds + interval_seconds, interval_seconds))
        
        df['time_bin'] = pd.cut(df['seconds'], bins=time_bins, labels=time_bins[:-1])
        
        # Calculate average sentiment and message count per interval
        grouped = df.groupby('time_bin').agg({
            'sentiment': 'mean',
            'clean_message': 'count'
        }).reset_index()
        
        grouped.columns = ['time_bin', 'sentiment_score', 'message_count']
        grouped['time_seconds'] = grouped['time_bin'].astype(int)
        
        # Convert seconds to HH:MM:SS
        grouped['time_str'] = grouped['time_seconds'].apply(self._seconds_to_time)
        
        # Fill NaN with 0
        grouped['sentiment_score'] = grouped['sentiment_score'].fillna(0)
        
        self.sentiment_results = grouped
        return grouped
    
    def detect_mood_changes(self, threshold: float = 0.3, 
                           min_change: float = 0.2) -> List[Dict]:
        """
        Detect significant mood changes
        
        Args:
            threshold: Minimum absolute sentiment score to consider
            min_change: Minimum change in sentiment to detect
            
        Returns:
            List of mood change events with time, change amount, and type
        """
        if self.sentiment_results is None or len(self.sentiment_results) < 2:
            return []
        
        changes = []
        df = self.sentiment_results
        
        for i in range(1, len(df)):
            prev_score = df.iloc[i-1]['sentiment_score']
            curr_score = df.iloc[i]['sentiment_score']
            change = curr_score - prev_score
            
            # Detect significant changes
            if abs(change) >= min_change:
                change_type = self._classify_mood_change(curr_score, change)
                
                changes.append({
                    'time': df.iloc[i]['time_str'],
                    'time_seconds': df.iloc[i]['time_seconds'],
                    'sentiment_score': curr_score,
                    'change': change,
                    'type': change_type,
                    'description': self._get_change_description(change_type, change)
                })
        
        # Sort by absolute change (largest first)
        changes.sort(key=lambda x: abs(x['change']), reverse=True)
        
        self.mood_changes = changes
        return changes
    
    def _classify_mood_change(self, score: float, change: float) -> str:
        """Classify type of mood change"""
        if change > 0:
            if score > 0.5:
                return 'excitement'  # 흥분
            elif score > 0.2:
                return 'positive'    # 긍정
            else:
                return 'recovery'    # 회복
        else:
            if score < -0.3:
                return 'sadness'     # 슬픔
            elif score < 0:
                return 'negative'    # 부정
            else:
                return 'calm'        # 진정
    
    def _get_change_description(self, change_type: str, change: float) -> str:
        """Get Korean description for mood change"""
        descriptions = {
            'excitement': '흥분 분위기',
            'positive': '긍정적 분위기',
            'recovery': '분위기 회복',
            'sadness': '슬픈 분위기',
            'negative': '부정적 분위기',
            'calm': '분위기 진정'
        }
        
        intensity = '급격한' if abs(change) > 0.4 else '점진적'
        return f"{intensity} {descriptions.get(change_type, '분위기 변화')}"
    
    def _seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def export_mood_markers(self, output_path: str, top_n: int = 10) -> bool:
        """
        Export top mood changes as Premiere Pro markers
        
        Args:
            output_path: Output CSV file path
            top_n: Number of top changes to export
            
        Returns:
            True if successful
        """
        if not self.mood_changes:
            return False
        
        # Get top N changes
        top_changes = self.mood_changes[:top_n]
        
        markers = []
        for change in top_changes:
            markers.append({
                'Marker Name': f"분위기 변화 - {change['type']}",
                'Description': f"{change['description']} ({change['change']:+.2f})",
                'In': change['time'],
                'Out': '',
                'Duration': '',
                'Marker Type': 'Comment'
            })
        
        markers_df = pd.DataFrame(markers)
        markers_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return True
    
    def get_sentiment_timeline(self) -> Optional[pd.DataFrame]:
        """Get sentiment analysis timeline"""
        return self.sentiment_results
    
    def get_mood_changes(self) -> List[Dict]:
        """Get detected mood changes"""
        return self.mood_changes
