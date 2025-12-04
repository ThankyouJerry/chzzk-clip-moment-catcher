import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from wordcloud import WordCloud
import re
from datetime import datetime
from collections import Counter
import os


class ChzzkChatAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 채팅 분석기")
        self.root.geometry("1200x800")
        
        self.df = None
        self.keyword_results = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # CSV 파일 선택
        file_frame = ttk.LabelFrame(main_frame, text="CSV 파일", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.file_label = ttk.Label(file_frame, text="파일을 선택하세요")
        self.file_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        ttk.Button(file_frame, text="파일 선택", command=self.load_csv).grid(row=0, column=1, padx=5)
        
        # 키워드 분석 섹션
        keyword_frame = ttk.LabelFrame(main_frame, text="키워드 분석", padding="10")
        keyword_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        ttk.Label(keyword_frame, text="검색 키워드:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.keyword_entry = ttk.Entry(keyword_frame, width=30)
        self.keyword_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(keyword_frame, text="시간 간격 (분):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.StringVar(value="1")
        ttk.Entry(keyword_frame, textvariable=self.interval_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Button(keyword_frame, text="키워드 분석", command=self.analyze_keyword).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(keyword_frame, text="프리미어 마커 내보내기", command=self.export_premiere_markers).grid(row=3, column=0, columnspan=2, pady=5)
        
        # 워드클라우드 섹션
        wordcloud_frame = ttk.LabelFrame(main_frame, text="워드클라우드", padding="10")
        wordcloud_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        ttk.Button(wordcloud_frame, text="워드클라우드 생성", command=self.generate_wordcloud).grid(row=0, column=0, pady=10)
        ttk.Button(wordcloud_frame, text="워드클라우드 저장", command=self.save_wordcloud).grid(row=1, column=0, pady=5)
        
        # 결과 표시 영역
        result_frame = ttk.LabelFrame(main_frame, text="분석 결과", padding="10")
        result_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 캔버스 영역 (그래프/워드클라우드 표시)
        self.canvas_frame = ttk.Frame(result_frame)
        self.canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
    
    def load_csv(self):
        file_path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.df = pd.read_csv(file_path)
                self.file_label.config(text=f"로드됨: {os.path.basename(file_path)}")
                messagebox.showinfo("성공", f"{len(self.df)}개의 채팅 메시지를 로드했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일 로드 실패: {str(e)}")
    
    def time_to_seconds(self, time_str):
        """HH:MM:SS 형식을 초로 변환"""
        try:
            parts = time_str.split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            return 0
    
    def seconds_to_time(self, seconds):
        """초를 HH:MM:SS 형식으로 변환"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def clean_message(self, message):
        """이모티콘 제거 및 텍스트 정리"""
        if pd.isna(message):
            return ""
        # 이모티콘 패턴 제거 {: :}
        message = re.sub(r'\{:[^:]+:\}', '', str(message))
        # [후원 ...] 패턴에서 텍스트 추출
        message = re.sub(r'\[후원 \d+치즈\]\s*', '', message)
        # [구독] 패턴 제거
        message = re.sub(r'\[\d+개월 구독\]\s*\d*', '', message)
        return message.strip()
    
    def analyze_keyword(self):
        if self.df is None:
            messagebox.showwarning("경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("경고", "키워드를 입력하세요.")
            return
        
        try:
            interval_minutes = float(self.interval_var.get())
            interval_seconds = int(interval_minutes * 60)
        except:
            messagebox.showerror("오류", "올바른 시간 간격을 입력하세요.")
            return
        
        # 시간을 초로 변환
        self.df['seconds'] = self.df['재생시간'].apply(self.time_to_seconds)
        
        # 메시지 정리
        self.df['clean_message'] = self.df['메시지'].apply(self.clean_message)
        
        # 키워드 포함 메시지 필터링
        keyword_df = self.df[self.df['clean_message'].str.contains(keyword, case=False, na=False)]
        
        if len(keyword_df) == 0:
            messagebox.showinfo("결과", f"'{keyword}' 키워드를 포함한 메시지가 없습니다.")
            return
        
        # 시간 간격별로 그룹화
        max_seconds = self.df['seconds'].max()
        time_bins = list(range(0, max_seconds + interval_seconds, interval_seconds))
        keyword_df['time_bin'] = pd.cut(keyword_df['seconds'], bins=time_bins, labels=time_bins[:-1])
        
        # 각 시간 구간별 키워드 빈도 계산
        keyword_counts = keyword_df.groupby('time_bin').size()
        
        # 결과 저장
        self.keyword_results = pd.DataFrame({
            'time_seconds': keyword_counts.index.astype(int),
            'count': keyword_counts.values
        })
        self.keyword_results['time_str'] = self.keyword_results['time_seconds'].apply(self.seconds_to_time)
        
        # 그래프 그리기
        self.plot_keyword_analysis(keyword, interval_minutes)
        
        messagebox.showinfo("분석 완료", 
                          f"총 {len(keyword_df)}개의 '{keyword}' 메시지 발견\n"
                          f"가장 많이 언급된 시간: {self.keyword_results.loc[self.keyword_results['count'].idxmax(), 'time_str']}")
    
    def plot_keyword_analysis(self, keyword, interval_minutes):
        """키워드 분석 그래프 그리기"""
        # 기존 캔버스 제거
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(self.keyword_results['time_str'], self.keyword_results['count'], color='steelblue')
        ax.set_xlabel('시간')
        ax.set_ylabel('빈도')
        ax.set_title(f"'{keyword}' 키워드 출현 빈도 ({interval_minutes}분 간격)")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Tkinter 캔버스에 그래프 표시
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def export_premiere_markers(self):
        """프리미어 프로 마커 CSV 내보내기"""
        if self.keyword_results is None:
            messagebox.showwarning("경고", "먼저 키워드 분석을 수행하세요.")
            return
        
        keyword = self.keyword_entry.get().strip()
        
        # 프리미어 프로 마커 형식
        # Marker Name, Description, In, Out, Duration, Marker Type
        markers = []
        for _, row in self.keyword_results.iterrows():
            if row['count'] > 0:  # 빈도가 0보다 큰 경우만
                markers.append({
                    'Marker Name': f"{keyword} ({row['count']}회)",
                    'Description': f"{keyword} 키워드가 {row['count']}번 언급됨",
                    'In': row['time_str'],
                    'Out': '',
                    'Duration': '',
                    'Marker Type': 'Comment'
                })
        
        markers_df = pd.DataFrame(markers)
        
        # 파일 저장
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"premiere_markers_{keyword}.csv"
        )
        
        if file_path:
            markers_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            messagebox.showinfo("성공", f"프리미어 마커를 저장했습니다:\n{file_path}")
    
    def generate_wordcloud(self):
        """워드클라우드 생성"""
        if self.df is None:
            messagebox.showwarning("경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        # 메시지 정리 (이모티콘 제거)
        if 'clean_message' not in self.df.columns:
            self.df['clean_message'] = self.df['메시지'].apply(self.clean_message)
        
        # 시스템 메시지 제외
        text_messages = self.df[self.df['닉네임'] != '[SYSTEM]']['clean_message']
        text_messages = text_messages[text_messages.str.len() > 0]
        
        # 모든 텍스트 합치기
        all_text = ' '.join(text_messages)
        
        if not all_text.strip():
            messagebox.showwarning("경고", "분석할 텍스트가 없습니다.")
            return
        
        # 워드클라우드 생성
        wordcloud = WordCloud(
            font_path='/System/Library/Fonts/AppleSDGothicNeo.ttc',  # macOS 한글 폰트
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            max_words=100
        ).generate(all_text)
        
        # 기존 캔버스 제거
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        
        # 워드클라우드 표시
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('채팅 워드클라우드')
        plt.tight_layout()
        
        self.current_wordcloud = wordcloud
        
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def save_wordcloud(self):
        """워드클라우드 이미지 저장"""
        if not hasattr(self, 'current_wordcloud'):
            messagebox.showwarning("경고", "먼저 워드클라우드를 생성하세요.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            initialfile="wordcloud.png"
        )
        
        if file_path:
            self.current_wordcloud.to_file(file_path)
            messagebox.showinfo("성공", f"워드클라우드를 저장했습니다:\n{file_path}")


def main():
    root = tk.Tk()
    app = ChzzkChatAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
