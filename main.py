#!/usr/bin/env python3
"""
Telegram Bot Hoster Manager
A comprehensive bot to manage multiple Telegram bot deployments
"""

import os
import sys
import json
import zipfile
import subprocess
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
import shutil
import psutil
import asyncio
from typing import Dict, List, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

# Configuration
BOT_TOKEN = ""  # Replace with your bot token
PROJECTS_DIR = Path("projects")
LOGS_DIR = Path("logs")
MAX_LOG_LINES = 100
AUTHORIZED_USERS = []  # Add user IDs here for authorization, empty = all users allowed

# Ensure directories exist
PROJECTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Logging setup - VPS friendly (file only)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('hoster_bot.log')
    ]
)

# Disable httpx logging to reduce log noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class ProjectManager:
    """Manages bot projects and their processes"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.project_configs: Dict[str, dict] = {}
        self.load_projects()
    
    def load_projects(self):
        """Load existing projects from disk"""
        try:
            config_file = PROJECTS_DIR / "projects.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.project_configs = json.load(f)
        except Exception as e:
            logger.error(f"Error loading projects: {e}")
            self.project_configs = {}
    
    def save_projects(self):
        """Save project configurations to disk"""
        try:
            config_file = PROJECTS_DIR / "projects.json"
            with open(config_file, 'w') as f:
                json.dump(self.project_configs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving projects: {e}")
    
    def create_project(self, name: str) -> bool:
        """Create a new project directory"""
        try:
            project_path = PROJECTS_DIR / name
            project_path.mkdir(exist_ok=True)
            
            self.project_configs[name] = {
                'name': name,
                'path': str(project_path),
                'run_command': 'python3 main.py',
                'created_at': datetime.now().isoformat(),
                'status': 'stopped'
            }
            self.save_projects()
            return True
        except Exception as e:
            logger.error(f"Error creating project {name}: {e}")
            return False
    
    def get_projects(self) -> List[str]:
        """Get list of all projects"""
        return list(self.project_configs.keys())
    
    def project_exists(self, name: str) -> bool:
        """Check if project exists"""
        return name in self.project_configs
    
    def get_project_path(self, name: str) -> Path:
        """Get project directory path"""
        return Path(self.project_configs[name]['path'])
    
    def start_project(self, name: str) -> Tuple[bool, str]:
        """Start a project"""
        if not self.project_exists(name):
            return False, "Project not found"
        
        if name in self.processes and self.processes[name].poll() is None:
            return False, "Project is already running"
        
        try:
            project_path = self.get_project_path(name)
            run_command = self.project_configs[name].get('run_command', 'python3 main.py')
            
            # Create logs directory for project
            project_logs_dir = LOGS_DIR / name
            project_logs_dir.mkdir(exist_ok=True)
            
            log_file = project_logs_dir / "output.log"
            
            # Start the process
            process = subprocess.Popen(
                run_command.split(),
                cwd=project_path,
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes[name] = process
            self.project_configs[name]['status'] = 'running'
            self.project_configs[name]['pid'] = process.pid
            self.save_projects()
            
            return True, f"Project started with PID {process.pid}"
        
        except Exception as e:
            logger.error(f"Error starting project {name}: {e}")
            return False, f"Error: {str(e)}"
    
    def stop_project(self, name: str) -> Tuple[bool, str]:
        """Stop a project"""
        if name not in self.processes:
            return False, "Project is not running"
        
        try:
            process = self.processes[name]
            if process.poll() is None:  # Process is still running
                process.terminate()
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if doesn't terminate
                    process.wait()
            
            del self.processes[name]
            self.project_configs[name]['status'] = 'stopped'
            if 'pid' in self.project_configs[name]:
                del self.project_configs[name]['pid']
            self.save_projects()
            
            return True, "Project stopped successfully"
        
        except Exception as e:
            logger.error(f"Error stopping project {name}: {e}")
            return False, f"Error: {str(e)}"
    
    def restart_project(self, name: str) -> Tuple[bool, str]:
        """Restart a project"""
        stop_success, _ = self.stop_project(name)
        if stop_success or name not in self.processes:
            time.sleep(2)  # Brief pause between stop and start
            return self.start_project(name)
        return False, "Failed to stop project for restart"
    
    def get_project_status(self, name: str) -> str:
        """Get project status"""
        if not self.project_exists(name):
            return "❌ Not found"
        
        if name in self.processes:
            process = self.processes[name]
            if process.poll() is None:
                return f"🟢 Running (PID: {process.pid})"
            else:
                # Process died, clean up
                del self.processes[name]
                self.project_configs[name]['status'] = 'stopped'
                self.save_projects()
        
        return "🔴 Stopped"
    
    def get_project_logs(self, name: str, lines: int = 20) -> str:
        """Get recent logs for a project"""
        try:
            log_file = LOGS_DIR / name / "output.log"
            if not log_file.exists():
                return "No logs found"
            
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
                return ''.join(log_lines[-lines:]) or "Logs are empty"
        
        except Exception as e:
            return f"Error reading logs: {str(e)}"
    
    def get_project_usage(self, name: str) -> str:
        """Get resource usage for a project"""
        if name not in self.processes:
            return "Project is not running"
        
        try:
            process = self.processes[name]
            if process.poll() is not None:
                return "Process has stopped"
            
            ps_process = psutil.Process(process.pid)
            cpu_percent = ps_process.cpu_percent()
            memory_info = ps_process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            return f"🖥 CPU: {cpu_percent:.1f}%\n💾 Memory: {memory_mb:.1f} MB\n⏱ Uptime: {self.get_process_uptime(ps_process)}"
        
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return f"Unable to get usage info: {str(e)}"
    
    def get_process_uptime(self, ps_process) -> str:
        """Calculate process uptime"""
        try:
            create_time = ps_process.create_time()
            uptime_seconds = time.time() - create_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        except:
            return "Unknown"
    
    def install_dependencies(self, name: str) -> Tuple[bool, str]:
        """Install project dependencies"""
        if not self.project_exists(name):
            return False, "Project not found"
        
        try:
            project_path = self.get_project_path(name)
            requirements_file = project_path / "requirements.txt"
            
            if not requirements_file.exists():
                return False, "requirements.txt not found"
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                return True, "Dependencies installed successfully"
            else:
                return False, f"Error installing dependencies:\n{result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            logger.error(f"Error installing dependencies for {name}: {e}")
            return False, f"Error: {str(e)}"
    
    def update_run_command(self, name: str, command: str) -> bool:
        """Update the run command for a project"""
        if not self.project_exists(name):
            return False
        
        self.project_configs[name]['run_command'] = command
        self.save_projects()
        return True
    
    def delete_project(self, name: str) -> Tuple[bool, str]:
        """Delete a project and its resources"""
        if not self.project_exists(name):
            return False, "Project not found"
        
        # Stop project if running
        if name in self.processes:
            stopped, message = self.stop_project(name)
            if not stopped:
                return False, f"Unable to stop project before deletion: {message}"
        
        try:
            project_path = self.get_project_path(name)
            if project_path.exists():
                shutil.rmtree(project_path)
            
            project_logs_dir = LOGS_DIR / name
            if project_logs_dir.exists():
                shutil.rmtree(project_logs_dir)
            
            if name in self.project_configs:
                del self.project_configs[name]
                self.save_projects()
            
            return True, f"Project '{name}' deleted successfully."
        except Exception as e:
            logger.error(f"Error deleting project {name}: {e}")
            return False, f"Error deleting project: {str(e)}"

# Global project manager instance
project_manager = ProjectManager()

# Authorization decorator
def authorized_only(func):
    """Decorator to restrict access to authorized users"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if AUTHORIZED_USERS and update.effective_user.id not in AUTHORIZED_USERS:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Bot handlers
@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    keyboard = [
        [KeyboardButton("🆕 New Project"), KeyboardButton("🚀 Deployment")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = """
🤖 **Bot Hoster Manager**

Welcome to your personal bot hosting service! 

**Features:**
• Create and manage multiple bot projects
• Start/Stop/Restart deployments
• Monitor resource usage and logs
• Install dependencies automatically
• Edit run commands

Choose an option from the menu below:
    """
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

@authorized_only
async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu selections"""
    text = update.message.text
    
    if text == "🆕 New Project":
        context.user_data['action'] = 'new_project'
        await update.message.reply_text(
            "🆕 **Create New Project**\n\nPlease enter a name for your new project:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif text == "🚀 Deployment":
        await show_deployment_menu(update, context)
    
    else:
        await handle_text_input(update, context)

async def show_deployment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deployment management menu"""
    projects = project_manager.get_projects()
    
    if not projects:
        await update.message.reply_text(
            "📭 **No Projects Found**\n\nYou haven't created any projects yet. Use '🆕 New Project' to get started!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = "🚀 **Deployment Management**\n\nSelect a project to manage:\n\n"
    keyboard = []
    
    for project in projects:
        status = project_manager.get_project_status(project)
        keyboard.append([InlineKeyboardButton(f"{project} {status}", callback_data=f"project_{project}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh_projects")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

@authorized_only
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input based on current action"""
    action = context.user_data.get('action')
    
    if action == 'new_project':
        project_name = update.message.text.strip()
        
        # Validate project name
        if not project_name or not project_name.replace('_', '').replace('-', '').isalnum():
            await update.message.reply_text(
                "❌ Invalid project name. Please use only letters, numbers, hyphens, and underscores."
            )
            return
        
        if project_manager.project_exists(project_name):
            await update.message.reply_text(f"❌ Project '{project_name}' already exists!")
            return
        
        if project_manager.create_project(project_name):
            context.user_data['current_project'] = project_name
            context.user_data['action'] = 'upload_files'
            
            await update.message.reply_text(
                f"✅ **Project '{project_name}' created successfully!**\n\n"
                "Now please upload your bot files:\n"
                "• Send a .zip archive containing your bot\n"
                "• Or send individual .py files\n\n"
                "💡 Make sure your main file is named `main.py` or update the run command later.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to create project. Please try again.")
    
    elif action == 'edit_run_command':
        project_name = context.user_data.get('current_project')
        new_command = update.message.text.strip()
        
        if project_manager.update_run_command(project_name, new_command):
            await update.message.reply_text(
                f"✅ Run command updated to: `{new_command}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to update run command.")
        
        context.user_data.clear()

@authorized_only
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    if context.user_data.get('action') != 'upload_files':
        await update.message.reply_text("❌ Please start by creating a new project first.")
        return
    
    project_name = context.user_data.get('current_project')
    if not project_name:
        await update.message.reply_text("❌ No active project found.")
        return
    
    document = update.message.document
    file_name = document.file_name
    
    try:
        # Download the file
        file = await context.bot.get_file(document.file_id)
        project_path = project_manager.get_project_path(project_name)
        
        if file_name.endswith('.zip'):
            # Handle zip file
            zip_path = project_path / file_name
            await file.download_to_drive(zip_path)
            
            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(project_path)
            
            # Remove the zip file after extraction
            zip_path.unlink()
            
            await update.message.reply_text(
                f"✅ **Zip file extracted successfully!**\n\n"
                f"📁 Files extracted to: `{project_path}`\n\n"
                "Your project is ready! Use '🚀 Deployment' to manage it.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif file_name.endswith('.py'):
            # Handle Python file
            file_path = project_path / file_name
            await file.download_to_drive(file_path)
            
            await update.message.reply_text(
                f"✅ **File '{file_name}' uploaded successfully!**\n\n"
                "You can upload more files or use '🚀 Deployment' to manage your project.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        else:
            await update.message.reply_text(
                "❌ Unsupported file type. Please upload .zip or .py files only."
            )
    
    except Exception as e:
        logger.error(f"Error handling document upload: {e}")
        await update.message.reply_text(f"❌ Error uploading file: {str(e)}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "refresh_projects":
        # Edit the message to refresh project list
        projects = project_manager.get_projects()
        
        if not projects:
            await query.edit_message_text("📭 **No Projects Found**\n\nCreate a new project first!")
            return
        
        message = "🚀 **Deployment Management**\n\nSelect a project to manage:\n\n"
        keyboard = []
        
        for project in projects:
            status = project_manager.get_project_status(project)
            keyboard.append([InlineKeyboardButton(f"{project} {status}", callback_data=f"project_{project}")])
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh_projects")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data.startswith("project_"):
        project_name = data.split("_", 1)[1]
        await show_project_menu(query, context, project_name)
    
    elif data.startswith("action_"):
        parts = data.split("_", 2)
        action = parts[1]
        project_name = parts[2]
        await handle_project_action(query, context, action, project_name)

async def show_project_menu(query, context: ContextTypes.DEFAULT_TYPE, project_name: str):
    """Show project management menu"""
    status = project_manager.get_project_status(project_name)
    
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"action_start_{project_name}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"action_stop_{project_name}")
        ],
        [
            InlineKeyboardButton("🔄 Restart", callback_data=f"action_restart_{project_name}"),
            InlineKeyboardButton("📊 Status", callback_data=f"action_status_{project_name}")
        ],
        [
            InlineKeyboardButton("📋 Logs", callback_data=f"action_logs_{project_name}"),
            InlineKeyboardButton("💻 Usage", callback_data=f"action_usage_{project_name}")
        ],
        [
            InlineKeyboardButton("📦 Install Deps", callback_data=f"action_install_{project_name}"),
            InlineKeyboardButton("⚙️ Edit Command", callback_data=f"action_edit_cmd_{project_name}")
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"action_delete_{project_name}")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="refresh_projects")]
    ]
    
    message = f"🔧 **Project: {project_name}**\n\n**Status:** {status}\n\nChoose an action:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_project_action(query, context: ContextTypes.DEFAULT_TYPE, action: str, project_name: str):
    """Handle project actions"""
    if action == "start":
        success, message = project_manager.start_project(project_name)
        status_emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{status_emoji} **Start Project**\n\n{message}")
    
    elif action == "stop":
        success, message = project_manager.stop_project(project_name)
        status_emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{status_emoji} **Stop Project**\n\n{message}")
    
    elif action == "restart":
        await query.edit_message_text("🔄 **Restarting project...**")
        success, message = project_manager.restart_project(project_name)
        status_emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{status_emoji} **Restart Project**\n\n{message}")
    
    elif action == "status":
        status = project_manager.get_project_status(project_name)
        await query.edit_message_text(f"📊 **Project Status**\n\n**{project_name}:** {status}")
    
    elif action == "logs":
        logs = project_manager.get_project_logs(project_name, 30)
        # Truncate logs if too long for Telegram
        if len(logs) > 4000:
            logs = logs[-4000:] + "\n\n... (truncated)"
        
        await query.edit_message_text(
            f"📋 **Recent Logs - {project_name}**\n\n```\n{logs}\n```",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif action == "usage":
        usage_info = project_manager.get_project_usage(project_name)
        await query.edit_message_text(f"💻 **Resource Usage - {project_name}**\n\n{usage_info}")
    
    elif action == "install":
        await query.edit_message_text("📦 **Installing dependencies...**")
        success, message = project_manager.install_dependencies(project_name)
        status_emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{status_emoji} **Install Dependencies**\n\n{message}")
    
    elif action == "edit_cmd":
        context.user_data['action'] = 'edit_run_command'
        context.user_data['current_project'] = project_name
        
        await query.edit_message_text(
            f"⚙️ **Edit Run Command**\n\n"
            f"Please send the new run command for **{project_name}**:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif action == "delete":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, delete", callback_data=f"action_deleteconfirm_{project_name}")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"project_{project_name}")
            ]
        ])
        await query.edit_message_text(
            f"🗑️ **Delete Project**\n\n"
            f"Are you sure you want to delete **{project_name}**? This cannot be undone.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif action == "deleteconfirm":
        success, message = project_manager.delete_project(project_name)
        status_emoji = "✅" if success else "❌"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="refresh_projects")]])
        await query.edit_message_text(
            f"{status_emoji} **Delete Project**\n\n{message}",
            reply_markup=keyboard
        )

def main():
    """Main function to run the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Start the bot
    logger.info("Bot started successfully!")
    
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        
        # Stop all running processes
        for name, process in project_manager.processes.items():
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN not configured")
        sys.exit(1)
    
    main()
