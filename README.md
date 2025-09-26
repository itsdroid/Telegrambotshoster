# 🤖 Telegram Bot Hoster Manager

A comprehensive Telegram bot management system that allows you to deploy, manage, and monitor multiple Telegram bots from a single interface. Perfect for developers and bot enthusiasts who need to manage multiple bot deployments efficiently.

## ✨ Features

- **🆕 Project Management**: Create and organize multiple bot projects
- **🚀 Deployment Control**: Start, stop, and restart bots with simple commands
- **📊 Real-time Monitoring**: Monitor CPU usage, memory consumption, and uptime
- **📋 Log Management**: View real-time logs and debug information
- **📦 Dependency Management**: Automatic installation of project dependencies
- **⚙️ Configuration**: Customizable run commands for each project
- **🔐 Authorization**: User-based access control for security
- **📁 File Upload**: Easy file and archive upload via Telegram
- **🔄 Auto-restart**: Automatic process recovery and restart capabilities

## 🏗️ Project Structure

```
TG/Hoster/
├── main.py                 # Main bot application
├── requirements.txt        # Python dependencies
├── start.sh               # VPS startup script
├── stop.sh                # Bot stop script
├── bot-hoster.service     # Systemd service configuration
├── projects/              # Directory for hosted bot projects
├── logs/                  # Log files for each project
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone or download the project:**
   ```bash
   git clone <repository-url>
   cd TG/Hoster
   ```

2. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure your bot token:**
   Edit `main.py` and replace the `BOT_TOKEN` with your actual bot token:
   ```python
   BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
   ```

4. **Run the bot:**
   ```bash
   python3 main.py
   ```

### Quick VPS Deployment

For VPS deployment, use the provided scripts:

```bash
# Make scripts executable
chmod +x start.sh stop.sh

# Start the bot
./start.sh

# Stop the bot
./stop.sh
```

## 📖 Usage Guide

### Getting Started

1. Start a conversation with your bot on Telegram
2. Send `/start` to see the main menu
3. Use the keyboard buttons to navigate:
   - **🆕 New Project**: Create a new bot project
   - **🚀 Deployment**: Manage existing projects

### Creating a New Project

1. Click **🆕 New Project**
2. Enter a project name (alphanumeric, hyphens, and underscores only)
3. Upload your bot files:
   - Send a `.zip` archive containing your bot
   - Or send individual `.py` files
4. Your project is ready for deployment!

### Managing Projects

1. Click **🚀 Deployment** to see all projects
2. Select a project to access management options:
   - **▶️ Start**: Launch the bot
   - **⏹️ Stop**: Stop the running bot
   - **🔄 Restart**: Restart the bot
   - **📊 Status**: Check current status
   - **📋 Logs**: View recent logs
   - **💻 Usage**: Monitor resource usage
   - **📦 Install Deps**: Install requirements.txt dependencies
   - **⚙️ Edit Command**: Modify the run command

## ⚙️ Configuration

### Bot Token Configuration

Edit the `BOT_TOKEN` variable in `main.py`:

```python
BOT_TOKEN = "432344344:453434fdfhkfhdfff"  # Replace with your token
```

### User Authorization

To restrict access to specific users, add their Telegram user IDs to the `AUTHORIZED_USERS` list:

```python
AUTHORIZED_USERS = [123456789, 987654321]  # Add user IDs here
```

Leave empty (`[]`) to allow all users.

### Directory Configuration

- `PROJECTS_DIR`: Directory where bot projects are stored (default: `projects/`)
- `LOGS_DIR`: Directory for log files (default: `logs/`)
- `MAX_LOG_LINES`: Maximum lines to display in log viewer (default: 100)

## 🖥️ VPS Deployment

### Using Shell Scripts

The project includes convenient shell scripts for VPS deployment:

**start.sh**: Starts the bot in background with dependency installation
**stop.sh**: Gracefully stops the running bot

### Using Systemd Service

For production deployment, use the systemd service:

1. **Edit the service file:**
   ```bash
   sudo nano bot-hoster.service
   ```
   Update the paths to match your installation directory.

2. **Install the service:**
   ```bash
   sudo cp bot-hoster.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable bot-hoster
   ```

3. **Start the service:**
   ```bash
   sudo systemctl start bot-hoster
   ```

4. **Check status:**
   ```bash
   sudo systemctl status bot-hoster
   ```

## 📋 Requirements

### Python Dependencies

- `python-telegram-bot==20.7`: Telegram Bot API wrapper
- `psutil==5.9.6`: System and process utilities

### System Requirements

- **RAM**: Minimum 512MB (1GB+ recommended)
- **Storage**: 1GB+ free space for projects and logs
- **Network**: Stable internet connection
- **OS**: Linux (Ubuntu/Debian recommended), Windows, macOS

## 🔧 Advanced Configuration

### Custom Run Commands

Each project can have a custom run command. Default is `python3 main.py`. You can modify this through the bot interface or by editing the project configuration.

### Log Management

Logs are automatically managed with rotation. Each project gets its own log directory under `logs/project_name/`.

### Resource Monitoring

The bot monitors:
- CPU usage percentage
- Memory consumption in MB
- Process uptime
- Process status (running/stopped)

## 🐛 Troubleshooting

### Common Issues

1. **Bot Token Error**
   - Ensure your bot token is correct and active
   - Check that the bot is not being used elsewhere

2. **Permission Denied**
   - Make sure scripts have execute permissions: `chmod +x start.sh stop.sh`
   - Check file/directory permissions

3. **Dependencies Not Found**
   - Run `pip3 install -r requirements.txt`
   - Ensure Python 3.7+ is installed

4. **Project Won't Start**
   - Check project logs through the bot interface
   - Verify the run command is correct
   - Ensure all dependencies are installed

### Log Files

- **Main bot logs**: `hoster_bot.log`
- **Project logs**: `logs/project_name/output.log`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🆘 Support

If you encounter any issues or need help:

1. Check the troubleshooting section above
2. Review the log files for error messages
3. Create an issue in the repository
4. Contact the maintainers

## 🔄 Updates

To update the bot hoster:

1. Backup your `projects/` directory
2. Download the latest version
3. Replace files (keep your `projects/` directory)
4. Restart the bot

---

**Made with ❤️ for the Telegram bot community**

*Happy bot hosting! 🚀*
