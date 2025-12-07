# 🎯 MeetMind - Intelligent Meeting Task Assignment

MeetMind is an AI-powered application that automatically extracts tasks from meeting audio recordings, assigns them to team members, and manages deadlines and priorities. It uses speech-to-text technology and natural language processing to transform meeting discussions into actionable task lists.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [API Endpoints](#api-endpoints)
- [Usage](#usage)
- [Configuration](#configuration)

## ✨ Features

### Core Functionality
- **Audio Processing**: Upload meeting audio files (.mp3, .wav, .m4a)
- **Speech-to-Text**: Automatic transcription using OpenAI Whisper
- **Task Extraction**: Intelligent extraction of actionable tasks from transcripts
- **Deadline Detection**: Automatic extraction of deadlines from temporal expressions
- **Priority Assignment**: Automatic priority detection (Critical, High, Medium, Low)
- **Dependency Mapping**: Identifies task dependencies and builds dependency graphs
- **Smart Assignment**: Automatically assigns tasks to team members based on:
  - Explicit mentions in conversation
  - Skill matching
  - Role matching
  - Workload balancing
- **Team Management**: Full CRUD interface for managing team members
- **Visual Dashboard**: Modern, responsive UI with task cards, filters, and dependency graphs
- **Dual View Modes**: Switch between card view and table view for tasks
- **Task Table View**: Comprehensive table with columns for description, assignee, deadline, priority, dependencies, and assignment reasoning

### Advanced Features
- **Context-Aware Extraction**: Handles vague references by looking at surrounding context
- **Workload Balancing**: Distributes tasks evenly across team members
- **Assignment Validation**: Validates and suggests alternative assignments
- **Entity Recognition**: Extracts people, technical terms, and time expressions
- **Skill Inference**: Automatically infers required skills from task descriptions

## 🛠 Tech Stack

### Backend
- **Python 3.12+**: Core programming language
- **FastAPI**: Modern, fast web framework for building APIs
- **OpenAI Whisper**: Speech-to-text transcription
- **Pydantic**: Data validation and settings management
- **python-dateutil**: Robust date parsing and relative date calculations
- **pydub**: Audio manipulation (requires FFmpeg)
- **NetworkX**: Dependency graph management

### Frontend
- **Vanilla JavaScript**: No framework dependencies
- **HTML5/CSS3**: Modern, responsive design
- **Chart.js**: Dependency graph visualization (via CDN)

### Audio Processing
- **FFmpeg**: Audio format conversion and preprocessing
- **pydub**: Audio segment manipulation

## 🏗 Project Architecture

### High-Level Flow

```
Audio Upload → Preprocessing → Transcription → Text Processing → Task Extraction → 
Enrichment (Entities, Deadlines, Priorities, Dependencies) → Skill Matching → 
Task Assignment → Validation → Response
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Upload   │  │ Tasks    │  │ Team     │               │
│  │ Handler  │  │ Manager  │  │ Manager  │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/REST API
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                   │
│  ┌──────────────────────────────────────────────┐       │
│  │         Audio Processing Pipeline            │       │
│  │  1. Audio Handler (Validation & Save)        │       │
│  │  2. Audio Preprocessing (Normalize, Convert) │       │
│  │  3. STT Service (Whisper Transcription)      │       │
│  └──────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────┐       │
│  │         NLP Processing Pipeline              │       │
│  │  1. Text Preprocessing                       │       │
│  │  2. Task Extraction                          │       │
│  │  3. Entity Recognition (NER)                 │       │
│  │  4. Deadline Extraction                      │       │
│  │  5. Priority Detection                       │       │
│  │  6. Dependency Extraction                    │       │
│  │  7. Skill Matching                           │       │
│  │  8. Task Assignment                          │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Storage                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Audio Files  │  │ Transcripts  │  │ Team Data    │   │
│  │ (uploads/)   │  │ (JSON)       │  │ (JSON)       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
MeetMind/
├── src/                          # Backend source code
│   ├── main.py                   # FastAPI application & API endpoints
│   ├── services/                 # Core business logic
│   │   ├── audio_handler.py      # Audio file validation & saving
│   │   ├── audio_preprocessing.py # Audio normalization & conversion
│   │   ├── stt_service.py         # Speech-to-text (Whisper)
│   │   ├── text_preprocessing.py  # Text cleaning & sentence splitting
│   │   ├── task_extraction.py     # Extract tasks from sentences
│   │   ├── ner.py                 # Named Entity Recognition
│   │   ├── deadline_extraction.py  # Extract deadlines
│   │   ├── priority_detection.py  # Detect task priorities
│   │   ├── dependency_extraction.py # Extract task dependencies
│   │   ├── skill_matching.py      # Match tasks to skills
│   │   ├── task_assignment.py     # Assign tasks to team members
│   │   └── team_loader.py         # Team data management
│   └── utils/
│       └── text_utils.py          # Text utility functions
│
├── models/                        # Pydantic data models
│   ├── task.py                    # Task model
│   ├── team.py                    # Team & TeamMember models
│   ├── nlp.py                     # PreprocessedSentence model
│   └── entities.py                # Entity model
│
├── frontend/                      # Frontend application
│   ├── index.html                 # Main HTML file
│   ├── css/
│   │   └── style.css              # Stylesheet
│   ├── js/
│   │   ├── api.js                 # API communication
│   │   ├── upload.js              # File upload handler
│   │   ├── tasks.js               # Task management
│   │   ├── ui.js                  # UI updates & modals
│   │   ├── graph.js               # Dependency graph visualization
│   │   └── team.js                # Team management
│   └── assets/                    # Static assets
│
├── data/                          # Data storage (gitignored)
│   ├── uploads/                   # Uploaded audio files
│   │   └── processed/             # Processed audio files
│   ├── transcripts/               # Transcript JSON files
│   └── team/
│       └── team_members.json      # Team member data
│
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── .gitignore                     # Git ignore rules
```

## 📦 Prerequisites

Before running the project, ensure you have:

1. **Python 3.12+** installed
2. **FFmpeg** installed and available in PATH
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg` (Ubuntu/Debian)
3. **Node.js** (optional, for local frontend server)
4. **Git** (for cloning the repository)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd MeetMind
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: The installation may take several minutes as it includes PyTorch and Whisper models.

### 4. Verify FFmpeg Installation

```bash
ffmpeg -version
```

If FFmpeg is not in PATH, you can set the `FFMPEG_PATH` environment variable:

```bash
# Windows
set FFMPEG_PATH=C:\path\to\ffmpeg.exe

# macOS/Linux
export FFMPEG_PATH=/usr/local/bin/ffmpeg
```

## 🏃 Running the Project

### Backend Server

1. **Activate virtual environment** (if not already activated):
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Start the FastAPI server**:
   ```bash
   uvicorn src.main:app --reload
   ```

   The API will be available at: `http://localhost:8000`
   
   API documentation: `http://localhost:8000/docs` (Swagger UI)

### Frontend

You have two options:

#### Option A: Direct File (Simplest)
- Simply open `frontend/index.html` in your browser
- Or double-click the file

#### Option B: Local Server (Recommended)
```bash
# Navigate to frontend directory
cd frontend

# Python HTTP Server
python -m http.server 8080

# Or Node.js (if you have it)
npx serve

# Then visit: http://localhost:8080
```

**Important**: Make sure the backend is running before using the frontend!

## 🔌 API Endpoints

### Audio Processing
- `POST /api/v1/audio/upload` - Upload and process audio file
  - Returns: Tasks, transcript, dependency graph, assignment summary

### Team Management
- `GET /api/v1/team` - Get all team members
- `POST /api/v1/team/members` - Add new team member
- `PUT /api/v1/team/members/{member_name}` - Update team member
- `DELETE /api/v1/team/members/{member_name}` - Delete team member
- `PUT /api/v1/team` - Update entire team

### Task Validation
- `POST /api/v1/tasks/validate` - Validate task assignments and get suggestions

### Health Check
- `GET /` - API health check

## 💻 Usage

### 1. Setup Team Members

1. Click "👥 Manage Team" in the header
2. Add team members with their roles and skills
3. Example:
   - Name: "John Doe"
   - Role: "Frontend Developer"
   - Skills: "React, JavaScript, UI bugs"

### 2. Upload Meeting Audio

1. Click "Browse Files" or drag & drop an audio file
2. Supported formats: `.mp3`, `.wav`, `.m4a`
3. Maximum file size: 25MB
4. Wait for processing to complete

### 3. View Results

After processing, you'll see:
- **Summary Cards**: Total tasks, assigned tasks, deadlines, critical tasks
- **Task Cards/Table**: Filterable list of extracted tasks in card or table format
- **Dependency Graph**: Visual representation of task dependencies
- **Transcript**: Full meeting transcript

### 4. Task Views

MeetMind offers two ways to view your tasks:

#### Card View (Default)
- Visual card-based layout
- Color-coded priority indicators
- Quick overview of task details
- Click any card to see full details

#### Table View
- Comprehensive tabular format
- Columns include:
  - **Task Description**: Full task text
  - **Assigned To**: Team member name (or "Unassigned")
  - **Deadline**: Formatted date and time
  - **Priority**: Color-coded priority badge
  - **Dependencies**: List of dependent task IDs
  - **Reason**: Assignment reasoning (hover for full text)
- Click any row to view full task details
- Perfect for quick scanning and comparison
- Responsive design with horizontal scroll on mobile

**Switching Views**: Use the "📋 Cards" and "📊 Table" toggle buttons above the filters to switch between views.

### 5. Task Details

Click any task card or table row to view:
- Full description
- Priority level
- Deadline
- Assigned team member
- Assignment reasoning
- Required skills
- Dependencies
- Technical terms

### 6. Filters

Use filters to:
- Filter by priority (Critical, High, Medium, Low)
- Filter by assignee
- Filter by status (Assigned/Unassigned)

**Note**: Filters work in both card and table views!

## ⚙️ Configuration

### Team Data

Team members are stored in `data/team/team_members.json`. You can:
- Edit manually (JSON format)
- Use the UI (recommended)

### API Base URL

If your backend runs on a different port/URL, edit `frontend/js/api.js`:

```javascript
const API_BASE_URL = 'http://your-backend-url:port';
```

### Environment Variables

- `FFMPEG_PATH`: Custom path to FFmpeg executable (optional)

## 🧪 Testing

Run unit tests:

```bash
# Activate virtual environment first
python -m pytest tests/
```

## 📝 Key Features Explained

### Task Display Views
- **Card View**: Visual, card-based layout perfect for browsing and quick overview
- **Table View**: Comprehensive tabular format with all task details in columns:
  - Task description, assignee, deadline, priority, dependencies, and assignment reasoning
  - Clickable rows for detailed view
  - Responsive design with horizontal scroll on mobile devices
- **View Toggle**: Easy switching between card and table views
- **Unified Filtering**: All filters work seamlessly in both view modes

### Task Extraction
- Identifies action items using heuristic rules
- Handles vague references by looking at context
- Extracts core tasks (removes conversational elements)

### Deadline Extraction
- Parses absolute dates (e.g., "January 15, 2024")
- Converts relative dates (e.g., "by tomorrow", "in 3 days")
- Only extracts when explicit deadline keywords are present

### Priority Detection
- Analyzes keywords (critical, urgent, blocking)
- Considers deadline proximity
- Assigns: Critical, High, Medium, Low

### Task Assignment
- **Priority 1**: Explicit assignment (name mentioned)
- **Priority 2**: Skill-based matching
- **Priority 3**: Role-based matching
- **Priority 4**: Workload-balanced fallback

### Dependency Extraction
- Identifies task dependencies ("depends on", "after", "first")
- Builds directed dependency graph
- Detects cycles and provides execution order

## 🐛 Troubleshooting

### FFmpeg Not Found
- Ensure FFmpeg is installed and in PATH
- Or set `FFMPEG_PATH` environment variable

### CORS Errors
- Backend CORS is configured to allow all origins
- Check that backend is running on the expected port

### File Upload Fails
- Check file size (max 25MB)
- Verify file format (.mp3, .wav, .m4a)
- Check browser console for errors

### Tasks Not Showing
- Check browser console for API errors
- Verify backend is processing correctly
- Check network tab in browser dev tools

### Audio Processing Slow
- First run downloads Whisper models (can be slow)
- Large audio files take longer to process
- Consider using shorter audio clips for testing

## 📚 Additional Resources

- **API Documentation**: Visit `http://localhost:8000/docs` when server is running
- **Frontend Quick Start**: See `frontend/QUICKSTART.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.  
You are free to use, modify, and distribute this software with proper credit.

## 👥 Authors

- **Mitesh Savaliya**  

---

**Happy Task Managing! 🎯**

