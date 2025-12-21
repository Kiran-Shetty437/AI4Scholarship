# AI Scholarship Application

A modern web application that helps Indian students find and apply for scholarships using AI-powered search and recommendations.

## Features

- 🔐 **User Authentication**: Secure signup with OTP verification via email
- 💬 **AI-Powered Chat**: Interactive chatbot for scholarship queries
- 🔍 **Google Search Integration**: Real-time scholarship search using Google Custom Search API
- 📱 **Responsive Design**: Beautiful, modern UI that works on mobile and desktop
- 💾 **Chat History**: Save and manage multiple chat conversations
- 🎨 **Modern UI**: Purple gradient theme with glassmorphism effects

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **AI**: OpenAI GPT-4o-mini
- **Search**: Google Custom Search API
- **Email**: SMTP (Gmail)

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-scholarship-app
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   FLASK_SECRET_KEY=your-secret-key-here
   OPENAI_API_KEY=your-openai-api-key
   GOOGLE_API_KEY=your-google-api-key
   SEARCH_ENGINE_ID=your-search-engine-id
   MAIL_USER=your-email@gmail.com
   MAIL_PASS=your-app-password
   ```

   **Note**: For Gmail, you'll need to generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   
   Open your browser and navigate to: `http://localhost:5000`

## Project Structure

```
ai-scholarship-app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
├── .gitignore            # Git ignore file
├── README.md             # Project documentation
├── templates/            # HTML templates
│   ├── chat.html        # Chat interface
│   ├── login.html       # Login page
│   ├── signup.html      # Signup page
│   ├── verify.html      # OTP verification
│   └── details.html    # Student details form
└── students.db          # SQLite database (created automatically)
```

## Usage

1. **Sign Up**: Create an account with email and password
2. **Verify**: Enter the OTP sent to your email
3. **Complete Profile**: Fill in your student details
4. **Chat**: Ask about scholarships using natural language
5. **Manage Chats**: Use the sidebar to create new chats or switch between conversations

## API Keys Required

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/)
- **Google Custom Search API**: 
  - Create a project in [Google Cloud Console](https://console.cloud.google.com/)
  - Enable Custom Search API
  - Create API key and Search Engine ID

## Features in Detail

### Chat Interface
- AI-powered responses using OpenAI GPT-4o-mini
- Real-time scholarship search integration
- Markdown support for formatted responses
- Chat history management

### User Management
- Secure password hashing
- Email-based OTP verification
- Session management
- User profile storage

### Responsive Design
- Mobile-first approach
- Tablet and desktop optimizations
- Touch-friendly interface
- Smooth animations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.

