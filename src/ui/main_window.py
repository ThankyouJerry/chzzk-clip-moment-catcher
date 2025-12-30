"""
Main Window for Chzzk Chat Analyzer
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QGroupBox, QFileDialog,
    QMessageBox, QScrollArea, QSlider
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
import platform
import os

from core.analyzer import ChatAnalyzer
from core.wordcloud_gen import WordCloudGenerator
from core.sentiment_analyzer import SentimentAnalyzer


# Configure Korean font for matplotlib
def setup_korean_font():
    """Setup Korean font for matplotlib"""
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
        if os.path.exists(font_path):
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
    elif system == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else:  # Linux
        plt.rcParams['font.family'] = 'NanumGothic'
    
    # Prevent minus sign from breaking
    plt.rcParams['axes.unicode_minus'] = False

# Setup font on module load
setup_korean_font()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = ChatAnalyzer()
        self.wordcloud_gen = WordCloudGenerator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.current_file = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("치지직 클립 모먼트 캐처")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(900, 700)  # Prevent window from being too small
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with reduced spacing
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title_label = QLabel("치지직 클립 모먼트 캐처")
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)
        
        # File selection group
        file_group = self.create_file_group()
        main_layout.addWidget(file_group)
        
        # Analysis controls with reduced spacing
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Keyword analysis group
        keyword_group = self.create_keyword_group()
        keyword_group.setMaximumHeight(280)
        controls_layout.addWidget(keyword_group, 1)
        
        # Sentiment analysis group
        sentiment_group = self.create_sentiment_group()
        sentiment_group.setMaximumHeight(280)
        controls_layout.addWidget(sentiment_group, 1)
        
        # Wordcloud group
        wordcloud_group = self.create_wordcloud_group()
        wordcloud_group.setMaximumHeight(280)
        controls_layout.addWidget(wordcloud_group, 1)
        
        main_layout.addLayout(controls_layout)
        
        # Results area
        results_group = self.create_results_group()
        main_layout.addWidget(results_group, 1)
    
    def create_file_group(self) -> QGroupBox:
        """Create file selection group"""
        group = QGroupBox("CSV 파일")
        layout = QHBoxLayout()
        
        self.file_label = QLabel("파일을 선택하세요")
        self.file_label.setObjectName("subtitleLabel")
        layout.addWidget(self.file_label, 1)
        
        load_btn = QPushButton("파일 선택")
        load_btn.clicked.connect(self.load_csv)
        layout.addWidget(load_btn)
        
        group.setLayout(layout)
        return group
    
    def create_keyword_group(self) -> QGroupBox:
        """Create keyword analysis group"""
        group = QGroupBox("키워드 분석")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Keyword input
        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("검색 키워드:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("예: ㅋㅋ, ㅠㅠ, 레전드")
        keyword_layout.addWidget(self.keyword_input, 1)
        layout.addLayout(keyword_layout)
        
        # Interval input and sensitivity on same row
        interval_sensitivity_layout = QHBoxLayout()
        
        # Interval input
        interval_sensitivity_layout.addWidget(QLabel("간격(분):"))
        self.interval_input = QLineEdit("1")
        self.interval_input.setMaximumWidth(50)
        interval_sensitivity_layout.addWidget(self.interval_input)
        
        interval_sensitivity_layout.addSpacing(15)
        
        # Sensitivity slider (compact inline)
        interval_sensitivity_layout.addWidget(QLabel("민감도:"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(10)  # 1.0
        self.sensitivity_slider.setMaximum(30)  # 3.0
        self.sensitivity_slider.setValue(20)    # 2.0 (default)
        self.sensitivity_slider.setMaximumWidth(100)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity_label)
        self.sensitivity_slider.setToolTip(
            "낮음: 큰 반응만 포착\n"
            "보통: 균형잡힌 감지\n"
            "높음: 작은 반응도 포착"
        )
        interval_sensitivity_layout.addWidget(self.sensitivity_slider)
        
        self.sensitivity_value_label = QLabel("보통")
        self.sensitivity_value_label.setStyleSheet("font-size: 11px;")
        interval_sensitivity_layout.addWidget(self.sensitivity_value_label)
        
        interval_sensitivity_layout.addStretch()
        layout.addLayout(interval_sensitivity_layout)
        
        # Analyze button
        analyze_btn = QPushButton("키워드 분석")
        analyze_btn.clicked.connect(self.analyze_keyword)
        layout.addWidget(analyze_btn)
        
        # Export button
        export_btn = QPushButton("프리미어 마커 내보내기")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self.export_premiere_markers)
        layout.addWidget(export_btn)
        
        # Chat density button
        density_btn = QPushButton("채팅 밀도 분석")
        density_btn.setObjectName("secondaryButton")
        density_btn.clicked.connect(self.analyze_chat_density)
        density_btn.setToolTip("키워드 없이 채팅이 급증한 하이라이트 구간을 찾습니다")
        layout.addWidget(density_btn)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_sentiment_group(self) -> QGroupBox:
        """Create sentiment analysis group"""
        group = QGroupBox("분위기 분석")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Interval input
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("시간 간격 (분):"))
        self.sentiment_interval_input = QLineEdit("1")
        self.sentiment_interval_input.setMaximumWidth(100)
        interval_layout.addWidget(self.sentiment_interval_input)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)
        
        # Analyze button
        analyze_btn = QPushButton("분위기 분석")
        analyze_btn.clicked.connect(self.analyze_sentiment)
        layout.addWidget(analyze_btn)
        
        # Find changes button
        changes_btn = QPushButton("변화 지점 찾기")
        changes_btn.setObjectName("secondaryButton")
        changes_btn.clicked.connect(self.find_mood_changes)
        layout.addWidget(changes_btn)
        
        # Export button
        export_btn = QPushButton("분위기 마커 내보내기")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self.export_mood_markers)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_wordcloud_group(self) -> QGroupBox:
        """Create wordcloud group"""
        group = QGroupBox("워드클라우드")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Generate button
        generate_btn = QPushButton("워드클라우드 생성")
        generate_btn.clicked.connect(self.generate_wordcloud)
        layout.addWidget(generate_btn)
        
        # Save button
        save_btn = QPushButton("워드클라우드 저장")
        save_btn.setObjectName("secondaryButton")
        save_btn.clicked.connect(self.save_wordcloud)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_results_group(self) -> QGroupBox:
        """Create results display group"""
        group = QGroupBox("분석 결과")
        layout = QVBoxLayout()
        
        # Scroll area for canvas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Canvas container
        self.canvas_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.canvas_container)
        layout.addWidget(scroll)
        
        group.setLayout(layout)
        return group
    
    def load_csv(self):
        """Load CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "CSV 파일 선택",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                count = self.analyzer.load_csv(file_path)
                self.current_file = file_path
                filename = os.path.basename(file_path)
                self.file_label.setText(f"로드됨: {filename}")
                
                QMessageBox.information(
                    self,
                    "성공",
                    f"{count:,}개의 채팅 메시지를 로드했습니다."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "오류",
                    f"파일 로드 실패:\n{str(e)}"
                )
    
    def update_sensitivity_label(self, value):
        """Update sensitivity label based on slider value"""
        sensitivity = value / 10.0
        if sensitivity <= 1.5:
            label = "낮음"
        elif sensitivity <= 2.5:
            label = "보통"
        else:
            label = "높음"
        self.sensitivity_value_label.setText(f"{label} ({sensitivity:.1f})")
    
    def analyze_chat_density(self):
        """Analyze chat density to find highlight moments without keywords"""
        if self.analyzer.df is None:
            QMessageBox.warning(self, "경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        try:
            interval = float(self.interval_input.text())
        except ValueError:
            QMessageBox.critical(self, "오류", "올바른 시간 간격을 입력하세요.")
            return
        
        # Get sensitivity value
        sensitivity = self.sensitivity_slider.value() / 10.0
        
        try:
            result = self.analyzer.analyze_chat_density(interval, sensitivity)
            
            # Plot graph
            self.plot_density_graph(interval)
            
            # Build result message
            peak_msg = f"가장 활발한 시간: {result['peak_time']}" if result['peak_time'] else "유의미한 피크를 찾지 못했습니다"
            
            QMessageBox.information(
                self,
                "분석 완료",
                f"채팅 밀도 분석 완료\n\n"
                f"총 {result['total_count']:,}개의 메시지 분석\n"
                f"{peak_msg}\n"
                f"하이라이트 구간: {result['spike_count']}개\n\n"
                f"민감도: {sensitivity:.1f} (평균+{sensitivity}σ 이상만 표시)"
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"분석 실패:\n{str(e)}")
    
    def analyze_keyword(self):
        """Analyze keyword frequency"""
        if self.analyzer.df is None:
            QMessageBox.warning(self, "경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "경고", "키워드를 입력하세요.")
            return
        
        try:
            interval = float(self.interval_input.text())
        except ValueError:
            QMessageBox.critical(self, "오류", "올바른 시간 간격을 입력하세요.")
            return
        
        # Get sensitivity value (slider value / 10 to get 1.0-3.0 range)
        sensitivity = self.sensitivity_slider.value() / 10.0
        
        try:
            result = self.analyzer.analyze_keyword(keyword, interval, sensitivity)
            
            if result['total_count'] == 0:
                QMessageBox.information(
                    self,
                    "결과",
                    f"'{keyword}' 키워드를 포함한 메시지가 없습니다."
                )
                return
            
            # Plot graph
            self.plot_keyword_graph(keyword, interval)
            
            # Build result message
            peak_msg = f"가장 많이 언급된 시간: {result['peak_time']}" if result['peak_time'] else "유의미한 피크를 찾지 못했습니다"
            
            QMessageBox.information(
                self,
                "분석 완료",
                f"총 {result['total_count']:,}개의 '{keyword}' 메시지 발견\n"
                f"{peak_msg}\n\n"
                f"민감도: {sensitivity:.1f} (평균+{sensitivity}σ 이상만 표시)"
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"분석 실패:\n{str(e)}")
    
    def plot_keyword_graph(self, keyword: str, interval: float):
        """Plot keyword frequency graph"""
        # Clear previous canvas
        for i in reversed(range(self.canvas_layout.count())):
            self.canvas_layout.itemAt(i).widget().setParent(None)
        
        # Get data
        timeline = self.analyzer.get_keyword_timeline()
        if timeline is None:
            return
        
        # Create figure with larger height
        fig = Figure(figsize=(12, 7), facecolor='#2a2a3e')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2a2a3e')
        
        # Plot bar chart
        x_positions = range(len(timeline))
        ax.bar(x_positions, timeline['count'], color='#6366f1', width=0.8)
        
        # Set x-axis labels - show every nth label to avoid overlap
        num_labels = len(timeline)
        if num_labels > 30:
            step = num_labels // 20  # Show ~20 labels
        elif num_labels > 15:
            step = 2
        else:
            step = 1
        
        # Set ticks and labels
        tick_positions = list(range(0, num_labels, step))
        tick_labels = [timeline['time_str'].iloc[i] for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        
        ax.set_ylabel('빈도', color='#e0e0e0', fontsize=10)
        ax.set_title(f"'{keyword}' 키워드 빈도 ({interval}분)", 
                     color='#e0e0e0', fontsize=11, fontweight='bold', pad=10)
        ax.tick_params(axis='x', colors='#e0e0e0', labelsize=8)
        ax.tick_params(axis='y', colors='#e0e0e0', labelsize=8)
        ax.spines['bottom'].set_color('#3a3a4e')
        ax.spines['left'].set_color('#3a3a4e')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add grid for better readability
        ax.grid(axis='y', alpha=0.2, color='#e0e0e0', linestyle='--', linewidth=0.5)
        
        # Adjust layout: [left, bottom, right, top]
        fig.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.20)
        
        # Create canvas
        canvas = FigureCanvasQTAgg(fig)
        self.canvas_layout.addWidget(canvas)
    
    def plot_density_graph(self, interval: float):
        """Plot chat density graph"""
        # Clear previous canvas
        for i in reversed(range(self.canvas_layout.count())):
            self.canvas_layout.itemAt(i).widget().setParent(None)
        
        # Get data
        timeline = self.analyzer.get_keyword_timeline()
        if timeline is None:
            return
        
        # Create figure with larger height
        fig = Figure(figsize=(12, 7), facecolor='#2a2a3e')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2a2a3e')
        
        # Plot bar chart with gradient colors
        x_positions = range(len(timeline))
        colors = ['#f59e0b' if count > timeline['count'].mean() * 1.5 else '#6366f1' 
                  for count in timeline['count']]
        ax.bar(x_positions, timeline['count'], color=colors, width=0.8)
        
        # Set x-axis labels
        num_labels = len(timeline)
        if num_labels > 30:
            step = num_labels // 20
        elif num_labels > 15:
            step = 2
        else:
            step = 1
        
        tick_positions = list(range(0, num_labels, step))
        tick_labels = [timeline['time_str'].iloc[i] for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        
        ax.set_ylabel('채팅 수', color='#e0e0e0', fontsize=10)
        ax.set_title(f'채팅 밀도 ({interval}분)', 
                     color='#e0e0e0', fontsize=11, fontweight='bold', pad=10)
        ax.tick_params(axis='x', colors='#e0e0e0', labelsize=8)
        ax.tick_params(axis='y', colors='#e0e0e0', labelsize=8)
        ax.spines['bottom'].set_color('#3a3a4e')
        ax.spines['left'].set_color('#3a3a4e')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add grid
        ax.grid(axis='y', alpha=0.2, color='#e0e0e0', linestyle='--', linewidth=0.5)
        
        # Adjust layout: [left, bottom, right, top]
        fig.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.20)
        
        # Create canvas
        canvas = FigureCanvasQTAgg(fig)
        self.canvas_layout.addWidget(canvas)
    
    def export_premiere_markers(self):
        """Export Premiere Pro markers"""
        if self.analyzer.get_keyword_timeline() is None:
            QMessageBox.warning(self, "경고", "먼저 키워드 분석을 수행하세요.")
            return
        
        keyword = self.keyword_input.text().strip()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "프리미어 마커 저장",
            f"premiere_markers_{keyword}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                self.analyzer.export_premiere_csv(file_path, keyword)
                QMessageBox.information(
                    self,
                    "성공",
                    f"프리미어 마커를 저장했습니다:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패:\n{str(e)}")
    
    def generate_wordcloud(self):
        """Generate wordcloud"""
        if self.analyzer.df is None:
            QMessageBox.warning(self, "경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        try:
            text = self.analyzer.get_all_text()
            
            if not text.strip():
                QMessageBox.warning(self, "경고", "분석할 텍스트가 없습니다.")
                return
            
            # Generate wordcloud
            success = self.wordcloud_gen.generate(text)
            
            if not success:
                QMessageBox.warning(self, "경고", "워드클라우드 생성 실패")
                return
            
            # Display wordcloud
            self.display_wordcloud()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"워드클라우드 생성 실패:\n{str(e)}")
    
    def display_wordcloud(self):
        """Display wordcloud on canvas"""
        # Clear previous canvas
        for i in reversed(range(self.canvas_layout.count())):
            self.canvas_layout.itemAt(i).widget().setParent(None)
        
        wordcloud = self.wordcloud_gen.get_wordcloud()
        if wordcloud is None:
            return
        
        # Create figure with more padding for title
        fig = Figure(figsize=(12, 6), facecolor='#2a2a3e')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2a2a3e')
        
        # Display wordcloud
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('채팅 워드클라우드', color='#e0e0e0', fontsize=14, 
                     fontweight='bold', pad=20)
        
        # Adjust layout with more padding
        fig.tight_layout(pad=2.0)
        
        # Create canvas
        canvas = FigureCanvasQTAgg(fig)
        self.canvas_layout.addWidget(canvas)
    
    def save_wordcloud(self):
        """Save wordcloud to file"""
        if self.wordcloud_gen.get_wordcloud() is None:
            QMessageBox.warning(self, "경고", "먼저 워드클라우드를 생성하세요.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "워드클라우드 저장",
            "wordcloud.png",
            "PNG Files (*.png)"
        )
        
        if file_path:
            try:
                self.wordcloud_gen.save(file_path)
                QMessageBox.information(
                    self,
                    "성공",
                    f"워드클라우드를 저장했습니다:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패:\n{str(e)}")
    def analyze_sentiment(self):
        """Analyze chat sentiment over time"""
        if self.analyzer.df is None:
            QMessageBox.warning(self, "경고", "먼저 CSV 파일을 로드하세요.")
            return
        
        try:
            interval = float(self.sentiment_interval_input.text())
        except ValueError:
            QMessageBox.critical(self, "오류", "올바른 시간 간격을 입력하세요.")
            return
        
        try:
            # Prepare data with seconds and clean messages
            if 'seconds' not in self.analyzer.df.columns:
                self.analyzer.df['seconds'] = self.analyzer.df['재생시간'].apply(
                    self.analyzer.time_to_seconds
                )
            
            if 'clean_message' not in self.analyzer.df.columns:
                self.analyzer.df['clean_message'] = self.analyzer.df['메시지'].apply(
                    self.analyzer.clean_message
                )
            
            # Analyze sentiment timeline
            timeline = self.sentiment_analyzer.analyze_timeline(
                self.analyzer.df, interval
            )
            
            if timeline is None or len(timeline) == 0:
                QMessageBox.warning(self, "경고", "분석할 데이터가 없습니다.")
                return
            
            # Plot sentiment graph
            self.plot_sentiment_graph(interval)
            
            # Calculate statistics
            avg_sentiment = timeline['sentiment_score'].mean()
            max_sentiment = timeline['sentiment_score'].max()
            min_sentiment = timeline['sentiment_score'].min()
            
            sentiment_desc = "긍정적" if avg_sentiment > 0.1 else "부정적" if avg_sentiment < -0.1 else "중립적"
            
            QMessageBox.information(
                self,
                "분석 완료",
                f"분위기 분석 완료\\n\\n"
                f"전체 분위기: {sentiment_desc} ({avg_sentiment:.2f})\\n"
                f"최고 긍정: {max_sentiment:.2f}\\n"
                f"최저 부정: {min_sentiment:.2f}"
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"분석 실패:\\n{str(e)}")
    
    def plot_sentiment_graph(self, interval: float):
        """Plot sentiment analysis graph with mood change markers"""
        # Clear previous canvas
        for i in reversed(range(self.canvas_layout.count())):
            self.canvas_layout.itemAt(i).widget().setParent(None)
        
        # Get data
        timeline = self.sentiment_analyzer.get_sentiment_timeline()
        if timeline is None or len(timeline) == 0:
            return
        
        # Detect mood changes for markers
        changes = self.sentiment_analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)
        
        # Create figure
        fig = Figure(figsize=(14, 8), facecolor='#2a2a3e')
        
        # Create two subplots
        ax1 = fig.add_subplot(211)  # Sentiment score
        ax2 = fig.add_subplot(212)  # Message frequency
        
        ax1.set_facecolor('#2a2a3e')
        ax2.set_facecolor('#2a2a3e')
        
        x_positions = range(len(timeline))
        
        # Plot 1: Sentiment score with color-coded areas
        sentiment_colors = ['#10b981' if s > 0.2 else '#ef4444' if s < -0.2 else '#6366f1' 
                           for s in timeline['sentiment_score']]
        
        # Fill area under curve
        positive_mask = timeline['sentiment_score'] > 0
        negative_mask = timeline['sentiment_score'] < 0
        
        ax1.fill_between(x_positions, 0, timeline['sentiment_score'], 
                         where=positive_mask, alpha=0.3, color='#10b981', label='긍정')
        ax1.fill_between(x_positions, 0, timeline['sentiment_score'], 
                         where=negative_mask, alpha=0.3, color='#ef4444', label='부정')
        
        # Plot line
        ax1.plot(x_positions, timeline['sentiment_score'], 
                color='#6366f1', linewidth=2.5, marker='o', markersize=3)
        
        # Add zero line
        ax1.axhline(y=0, color='#e0e0e0', linestyle='--', alpha=0.5, linewidth=1)
        
        # Add mood change markers
        if changes:
            for change in changes[:5]:  # Top 5 changes
                # Find x position
                time_idx = timeline[timeline['time_str'] == change['time']].index
                if len(time_idx) > 0:
                    x_pos = time_idx[0]
                    y_pos = timeline.iloc[x_pos]['sentiment_score']
                    
                    # Marker color based on type
                    marker_color = {
                        'excitement': '#f59e0b',
                        'positive': '#10b981',
                        'sadness': '#ef4444',
                        'negative': '#dc2626',
                        'recovery': '#8b5cf6',
                        'calm': '#6366f1'
                    }.get(change['type'], '#f59e0b')
                    
                    # Add vertical line
                    ax1.axvline(x=x_pos, color=marker_color, linestyle=':', alpha=0.6, linewidth=2)
                    ax2.axvline(x=x_pos, color=marker_color, linestyle=':', alpha=0.6, linewidth=2)
                    
                    # Add annotation
                    ax1.annotate(f"{change['type'][:3]}", 
                               xy=(x_pos, y_pos),
                               xytext=(0, 10),
                               textcoords='offset points',
                               ha='center',
                               fontsize=8,
                               color=marker_color,
                               weight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', 
                                       facecolor='#2a2a3e', 
                                       edgecolor=marker_color, 
                                       alpha=0.8))
        
        ax1.set_ylabel('감정 점수', color='#e0e0e0', fontsize=12, weight='bold')
        ax1.set_title(f'채팅 분위기 분석 ({interval}분 간격) - 점선: 주요 변화 지점', 
                     color='#e0e0e0', fontsize=15, fontweight='bold', pad=20)
        ax1.tick_params(axis='both', colors='#e0e0e0', labelsize=9)
        ax1.set_ylim(-1.1, 1.1)
        ax1.grid(axis='y', alpha=0.2, color='#e0e0e0', linestyle='--', linewidth=0.5)
        ax1.legend(loc='upper right', fontsize=9, framealpha=0.8)
        
        # Plot 2: Message frequency with gradient colors
        colors_freq = ['#8b5cf6' if timeline.iloc[i]['sentiment_score'] > 0 else '#6366f1' 
                      for i in range(len(timeline))]
        ax2.bar(x_positions, timeline['message_count'], 
               color=colors_freq, alpha=0.7, width=0.8)
        
        # Set x-axis labels for both plots
        num_labels = len(timeline)
        if num_labels > 30:
            step = num_labels // 20
        elif num_labels > 15:
            step = 2
        else:
            step = 1
        
        tick_positions = list(range(0, num_labels, step))
        tick_labels = [timeline['time_str'].iloc[i] for i in tick_positions]
        
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([])  # Hide x labels on top plot
        
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
        ax2.set_xlabel('시간', color='#e0e0e0', fontsize=12, weight='bold')
        ax2.set_ylabel('메시지 수', color='#e0e0e0', fontsize=12, weight='bold')
        ax2.tick_params(axis='both', colors='#e0e0e0', labelsize=9)
        ax2.grid(axis='y', alpha=0.2, color='#e0e0e0', linestyle='--', linewidth=0.5)
        
        # Style spines
        for ax in [ax1, ax2]:
            ax.spines['bottom'].set_color('#3a3a4e')
            ax.spines['left'].set_color('#3a3a4e')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        # Adjust layout with explicit spacing to ensure titles and labels are visible
        fig.subplots_adjust(left=0.08, right=0.95, top=0.94, bottom=0.18, hspace=0.35)
        
        # Create canvas
        canvas = FigureCanvasQTAgg(fig)
        self.canvas_layout.addWidget(canvas)
    
    def find_mood_changes(self):
        """Find and display mood change points"""
        if self.sentiment_analyzer.get_sentiment_timeline() is None:
            QMessageBox.warning(self, "경고", "먼저 분위기 분석을 수행하세요.")
            return
        
        try:
            # Detect mood changes
            changes = self.sentiment_analyzer.detect_mood_changes(
                threshold=0.3, min_change=0.2
            )
            
            if not changes:
                QMessageBox.information(
                    self, "결과", 
                    "뚜렷한 분위기 변화 지점을 찾지 못했습니다."
                )
                return
            
            # Show top 10 changes with icons
            top_changes = changes[:10]
            
            # Type icons and Korean names
            type_info = {
                'excitement': ('🔥', '흥분'),
                'positive': ('😊', '긍정'),
                'recovery': ('💪', '회복'),
                'sadness': ('😢', '슬픔'),
                'negative': ('😞', '부정'),
                'calm': ('😌', '진정')
            }
            
            message = "━━━━━━━━━━━━━━━━━━━━━━\n"
            message += "   주요 분위기 변화 지점\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for i, change in enumerate(top_changes, 1):
                icon, type_name = type_info.get(change['type'], ('📍', '변화'))
                
                # Change intensity indicator
                if abs(change['change']) > 0.5:
                    intensity = "⚡⚡⚡"
                elif abs(change['change']) > 0.3:
                    intensity = "⚡⚡"
                else:
                    intensity = "⚡"
                
                message += f"{i}. {icon} {change['time']}\n"
                message += f"   유형: {type_name} {intensity}\n"
                message += f"   변화: {change['change']:+.2f}\n"
                message += f"   점수: {change['sentiment_score']:.2f}\n"
                message += "   ─────────────────\n"
            
            message += "\n💡 그래프의 점선이 변화 지점입니다"
            
            QMessageBox.information(self, "분위기 변화 지점", message)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"분석 실패:\n{str(e)}")
    
    def export_mood_markers(self):
        """Export mood change markers for Premiere Pro"""
        if not self.sentiment_analyzer.get_mood_changes():
            QMessageBox.warning(self, "경고", "먼저 변화 지점을 찾아주세요.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "분위기 마커 저장",
            "mood_markers.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                success = self.sentiment_analyzer.export_mood_markers(
                    file_path, top_n=10
                )
                
                if success:
                    QMessageBox.information(
                        self,
                        "성공",
                        f"분위기 마커를 저장했습니다:\\n{file_path}"
                    )
                else:
                    QMessageBox.warning(self, "경고", "마커 생성 실패")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패:\\n{str(e)}")
