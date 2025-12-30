"""
Chat Analyzer - Core Analysis Logic
"""
import pandas as pd
import re
from typing import Optional, Dict, List


class ChatAnalyzer:
    """Analyzes Chzzk chat CSV files"""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.keyword_results: Optional[pd.DataFrame] = None
    
    def load_csv(self, file_path: str) -> int:
        """
        Load CSV file and return number of messages
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Number of messages loaded
        """
        self.df = pd.read_csv(file_path)
        return len(self.df)
    
    def time_to_seconds(self, time_str: str) -> int:
        """Convert HH:MM:SS to seconds"""
        try:
            parts = time_str.split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            return 0
    
    def seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def clean_message(self, message) -> str:
        """Remove emoticons and clean message text"""
        if pd.isna(message):
            return ""
        
        # Remove emoticon patterns {:emoji:}
        message = re.sub(r'\{:[^:]+:\}', '', str(message))
        
        # Remove donation patterns [후원 1000치즈]
        message = re.sub(r'\[후원 \d+치즈\]\s*', '', message)
        
        # Remove subscription patterns [3개월 구독]
        message = re.sub(r'\[\d+개월 구독\]\s*\d*', '', message)
        
        return message.strip()
    
    def analyze_keyword(self, keyword: str, interval_minutes: float, sensitivity: float = 2.0) -> Dict:
        """
        Analyze keyword frequency over time with Z-Score based filtering
        
        Args:
            keyword: Keyword to search for
            interval_minutes: Time interval in minutes
            sensitivity: Z-Score threshold (1.0=low, 2.0=normal, 3.0=high)
            
        Returns:
            Dictionary with analysis results
        """
        if self.df is None:
            raise ValueError("No CSV loaded")
        
        # Convert time to seconds
        self.df['seconds'] = self.df['재생시간'].apply(self.time_to_seconds)
        
        # Clean messages
        self.df['clean_message'] = self.df['메시지'].apply(self.clean_message)
        
        # Filter messages containing keyword (escape regex special chars)
        keyword_df = self.df[self.df['clean_message'].str.contains(re.escape(keyword), case=False, na=False, regex=True)]
        
        if len(keyword_df) == 0:
            return {
                'total_count': 0,
                'peak_time': None,
                'timeline': [],
                'sensitivity': sensitivity
            }
        
        # Group by time intervals
        interval_seconds = int(interval_minutes * 60)
        max_seconds = self.df['seconds'].max()
        time_bins = list(range(0, max_seconds + interval_seconds, interval_seconds))
        
        keyword_df['time_bin'] = pd.cut(keyword_df['seconds'], bins=time_bins, labels=time_bins[:-1])
        
        # Count keywords per interval
        keyword_counts = keyword_df.groupby('time_bin').size()
        
        # Z-Score based filtering
        mean = keyword_counts.mean()
        std = keyword_counts.std()
        
        # Avoid division by zero
        if std == 0:
            threshold = mean
        else:
            threshold = mean + (sensitivity * std)
        
        # Filter significant moments
        significant_indices = keyword_counts[keyword_counts >= threshold].index
        
        # Store results (only significant moments)
        self.keyword_results = pd.DataFrame({
            'time_seconds': significant_indices.astype(int),
            'count': keyword_counts[significant_indices].values
        })
        self.keyword_results['time_str'] = self.keyword_results['time_seconds'].apply(self.seconds_to_time)
        
        # Find peak time
        if len(self.keyword_results) > 0:
            peak_idx = self.keyword_results['count'].idxmax()
            peak_time = self.keyword_results.loc[peak_idx, 'time_str']
        else:
            peak_time = None
        
        return {
            'total_count': len(keyword_df),
            'peak_time': peak_time,
            'timeline': self.keyword_results.to_dict('records'),
            'sensitivity': sensitivity,
            'threshold': threshold,
            'mean': mean,
            'std': std
        }
    
    def analyze_chat_density(self, interval_minutes: float, sensitivity: float = 2.0) -> Dict:
        """
        Analyze chat density (message frequency) over time to find highlight moments
        
        Args:
            interval_minutes: Time interval in minutes
            sensitivity: Z-Score threshold (1.0=low, 2.0=normal, 3.0=high)
            
        Returns:
            Dictionary with analysis results
        """
        if self.df is None:
            raise ValueError("No CSV loaded")
        
        # Convert time to seconds if not already done
        if 'seconds' not in self.df.columns:
            self.df['seconds'] = self.df['재생시간'].apply(self.time_to_seconds)
        
        # Group by time intervals
        interval_seconds = int(interval_minutes * 60)
        max_seconds = self.df['seconds'].max()
        time_bins = list(range(0, max_seconds + interval_seconds, interval_seconds))
        
        self.df['time_bin'] = pd.cut(self.df['seconds'], bins=time_bins, labels=time_bins[:-1])
        
        # Count messages per interval
        message_counts = self.df.groupby('time_bin').size()
        
        # Z-Score based filtering
        mean = message_counts.mean()
        std = message_counts.std()
        
        # Avoid division by zero
        if std == 0:
            threshold = mean
        else:
            threshold = mean + (sensitivity * std)
        
        # Filter significant moments (chat spikes)
        significant_indices = message_counts[message_counts >= threshold].index
        
        # Store results (only significant moments)
        self.keyword_results = pd.DataFrame({
            'time_seconds': significant_indices.astype(int),
            'count': message_counts[significant_indices].values
        })
        self.keyword_results['time_str'] = self.keyword_results['time_seconds'].apply(self.seconds_to_time)
        
        # Find peak time
        if len(self.keyword_results) > 0:
            peak_idx = self.keyword_results['count'].idxmax()
            peak_time = self.keyword_results.loc[peak_idx, 'time_str']
        else:
            peak_time = None
        
        return {
            'total_count': len(self.df),
            'peak_time': peak_time,
            'timeline': self.keyword_results.to_dict('records'),
            'sensitivity': sensitivity,
            'threshold': threshold,
            'mean': mean,
            'std': std,
            'spike_count': len(self.keyword_results)
        }
    
    def get_keyword_timeline(self) -> Optional[pd.DataFrame]:
        """Get keyword analysis timeline"""
        return self.keyword_results
    
    def export_premiere_csv(self, output_path: str, keyword: str) -> bool:
        """
        Export Premiere Pro marker CSV
        
        Args:
            output_path: Output file path
            keyword: Keyword name for markers
            
        Returns:
            True if successful
        """
        if self.keyword_results is None:
            return False
        
        # Create Premiere Pro marker format
        markers = []
        for _, row in self.keyword_results.iterrows():
            if row['count'] > 0:
                markers.append({
                    'Marker Name': f"{keyword} ({row['count']}회)",
                    'Description': f"{keyword} 키워드가 {row['count']}번 언급됨",
                    'In': row['time_str'],
                    'Out': '',
                    'Duration': '',
                    'Marker Type': 'Comment'
                })
        
        markers_df = pd.DataFrame(markers)
        markers_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return True
    
    def export_edl(self, output_path: str, keyword: str) -> bool:
        """
        Export EDL (Edit Decision List) for DaVinci Resolve / Final Cut Pro
        
        Args:
            output_path: Output file path
            keyword: Keyword name for markers
            
        Returns:
            True if successful
        """
        if self.keyword_results is None:
            return False
        
        # EDL format:
        # 001  AX       V     C        00:00:10:00 00:00:10:00 00:00:10:00 00:00:10:00
        # * FROM CLIP NAME: marker_name
        
        edl_lines = []
        edl_lines.append("TITLE: Chzzk Chat Markers")
        edl_lines.append("FCM: NON-DROP FRAME")
        edl_lines.append("")
        
        for idx, (_, row) in enumerate(self.keyword_results.iterrows(), 1):
            if row['count'] > 0:
                # Convert time_str (HH:MM:SS) to timecode (HH:MM:SS:FF)
                timecode = f"{row['time_str']}:00"
                
                # EDL entry
                edl_lines.append(f"{idx:03d}  AX       V     C        {timecode} {timecode} {timecode} {timecode}")
                edl_lines.append(f"* FROM CLIP NAME: {keyword} ({row['count']}회)")
                edl_lines.append(f"* COMMENT: {keyword} 키워드가 {row['count']}번 언급됨")
                edl_lines.append("")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(edl_lines))
        
        return True
    
    def get_all_text(self) -> str:
        """Get all chat text for wordcloud"""
        if self.df is None:
            return ""
        
        # Clean messages if not already done
        if 'clean_message' not in self.df.columns:
            self.df['clean_message'] = self.df['메시지'].apply(self.clean_message)
        
        # Exclude system messages
        text_messages = self.df[self.df['닉네임'] != '[SYSTEM]']['clean_message']
        text_messages = text_messages[text_messages.str.len() > 0]
        
        return ' '.join(text_messages)
