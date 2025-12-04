"""
Main Window for Chzzk Chat Analyzer
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QGroupBox, QFileDialog,
    QMessageBox, QScrollArea
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
        self.current_file = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("치지직 클립 모먼트 캐처")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("치지직 클립 모먼트 캐처")
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)
        
        # File selection group
        file_group = self.create_file_group()
        main_layout.addWidget(file_group)
        
        # Analysis controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)
        
        # Keyword analysis group
        keyword_group = self.create_keyword_group()
        controls_layout.addWidget(keyword_group, 1)
        
        # Wordcloud group
        wordcloud_group = self.create_wordcloud_group()
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
        layout.setSpacing(12)
        
        # Keyword input
        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("검색 키워드:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("예: ㅋㅋ, 고키겡요")
        keyword_layout.addWidget(self.keyword_input, 1)
        layout.addLayout(keyword_layout)
        
        # Interval input
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("시간 간격 (분):"))
        self.interval_input = QLineEdit("1")
        self.interval_input.setMaximumWidth(100)
        interval_layout.addWidget(self.interval_input)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)
        
        # Analyze button
        analyze_btn = QPushButton("키워드 분석")
        analyze_btn.clicked.connect(self.analyze_keyword)
        layout.addWidget(analyze_btn)
        
        # Export button
        export_btn = QPushButton("프리미어 마커 내보내기")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self.export_premiere_markers)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_wordcloud_group(self) -> QGroupBox:
        """Create wordcloud group"""
        group = QGroupBox("워드클라우드")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
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
        
        try:
            result = self.analyzer.analyze_keyword(keyword, interval)
            
            if result['total_count'] == 0:
                QMessageBox.information(
                    self,
                    "결과",
                    f"'{keyword}' 키워드를 포함한 메시지가 없습니다."
                )
                return
            
            # Plot graph
            self.plot_keyword_graph(keyword, interval)
            
            QMessageBox.information(
                self,
                "분석 완료",
                f"총 {result['total_count']:,}개의 '{keyword}' 메시지 발견\n"
                f"가장 많이 언급된 시간: {result['peak_time']}"
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
        
        # Create figure
        fig = Figure(figsize=(12, 6), facecolor='#2a2a3e')
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
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        ax.set_xlabel('시간', color='#e0e0e0', fontsize=12)
        ax.set_ylabel('빈도', color='#e0e0e0', fontsize=12)
        ax.set_title(f"'{keyword}' 키워드 출현 빈도 ({interval}분 간격)", 
                     color='#e0e0e0', fontsize=14, fontweight='bold', pad=20)
        ax.tick_params(axis='x', colors='#e0e0e0', labelsize=9)
        ax.tick_params(axis='y', colors='#e0e0e0')
        ax.spines['bottom'].set_color('#3a3a4e')
        ax.spines['left'].set_color('#3a3a4e')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add grid for better readability
        ax.grid(axis='y', alpha=0.2, color='#e0e0e0', linestyle='--', linewidth=0.5)
        
        # Adjust layout with more padding
        fig.tight_layout(pad=2.0)
        
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
