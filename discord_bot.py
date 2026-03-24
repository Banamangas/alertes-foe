#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Bot Planificateur - Automated message scheduler for Discord
Sends scheduled messages for gaming events with French localization
"""

import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import datetime, timedelta, time
import pytz
from dotenv import load_dotenv
import json
import logging
from keep_alive import keep_alive
from typing import Optional, Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
class Config:
    """Configuration constants"""
    TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = int(os.getenv('CHANNEL_ID')) if os.getenv('CHANNEL_ID') else None
    
    # Messages
    THURSDAY_EVEN_MESSAGE = os.getenv('THURSDAY_EVEN_MESSAGE', 'Message du jeudi semaine paire !')
    THURSDAY_ODD_MESSAGE = os.getenv('THURSDAY_ODD_MESSAGE', 'Message du jeudi semaine impaire !')
    TUESDAY_MESSAGE = os.getenv('TUESDAY_MESSAGE', 'Message du mardi !')
    SUNDAY_MESSAGE = os.getenv('SUNDAY_MESSAGE', 'Message du dimanche !')
    
    # Timezone
    TZ = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Paris'))
    
    # Schedule times
    THURSDAY_TIME = time(7, 55)  # 7:55 AM
    TUESDAY_TIME = time(8, 0)    # 8:00 AM
    SUNDAY_TIME = time(18, 0)    # 6:00 PM
    
    # Catch-up window for Thursday messages (until 10:00 AM)
    THURSDAY_CATCHUP_TIME = time(10, 0)
    
    # Files
    DATES_FILE = "sent_dates.json"
    ONETIME_FILE = "onetime_messages.json"

class DayMapping:
    """Day name mappings between French and English"""
    FRENCH_TO_ENGLISH = {
        'lundi': 'monday',
        'mardi': 'tuesday', 
        'mercredi': 'wednesday',
        'jeudi': 'thursday',
        'vendredi': 'friday',
        'samedi': 'saturday',
        'dimanche': 'sunday'
    }
    
    ENGLISH_TO_FRENCH = {v: k for k, v in FRENCH_TO_ENGLISH.items()}
    
    FRENCH_DISPLAY = {
        'monday': 'Lundi', 'tuesday': 'Mardi', 'wednesday': 'Mercredi',
        'thursday': 'Jeudi', 'friday': 'Vendredi', 'saturday': 'Samedi', 'sunday': 'Dimanche'
    }

class MessageThemes:
    """Message themes and styling configuration"""
    THURSDAY_EVEN = {
        'color': discord.Color.purple(),
        'icon': '⚡',
        'title': '🌌 Incursions Quantiques',
        'info_fields': [
            ('📊 Semaine', 'Semaine {week_num} (Paire)', True),
            ('📅 Prochain', 'Jeudi prochain', True)
        ]
    }
    
    THURSDAY_ODD = {
        'color': discord.Color.red(),
        'icon': '⚔️',
        'title': '🏛️ Champs de Bataille',
        'info_fields': [
            ('📊 Semaine', 'Semaine {week_num} (Impaire)', True),
            ('📅 Prochain', 'Jeudi prochain', True)
        ]
    }
    
    TUESDAY = {
        'color': discord.Color.orange(),
        'icon': '🎯',
        'title': '🚀 EG - Début de Semaine',
        'info_fields': [
            ('⏰ Durée', 'Toute la semaine', True),
            ('📅 Fin', 'Lundi matin à 8h', True)
        ]
    }
    
    SUNDAY = {
        'color': discord.Color.blue(),
        'icon': '🏆',
        'title': '⏰ Rappel EG',
        'info_fields': [
            ('⚠️ Attention', 'Dernier rappel !', True),
            ('🕕 Temps restant', '14 heures', True)
        ]
    }

class ScheduledMessenger:
    """Handles scheduled message logic and persistence"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_sent_dates: Dict[str, Optional[datetime.date]] = {
            'thursday': None,
            'tuesday': None, 
            'sunday': None
        }
        self.onetime_messages: List[Dict[str, Any]] = []
        
        # Load data from files
        self.load_sent_dates()
        self.load_onetime_messages()
    
    def load_sent_dates(self) -> None:
        """Load previously sent dates from JSON file"""
        try:
            if os.path.exists(Config.DATES_FILE):
                with open(Config.DATES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert string dates back to date objects
                for day, date_str in data.items():
                    if date_str:
                        try:
                            self.last_sent_dates[day] = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            self.last_sent_dates[day] = None
                
                logger.info(f"Loaded sent dates from {Config.DATES_FILE}: {self.last_sent_dates}")
            else:
                logger.info(f"No existing {Config.DATES_FILE} found, starting fresh")
        except Exception as e:
            logger.warning(f"Error loading sent dates: {e}")
            logger.info("Starting with empty sent dates")
    
    def save_sent_dates(self) -> None:
        """Save current sent dates to JSON file"""
        try:
            # Convert date objects to strings for JSON serialization
            data = {}
            for day, date_obj in self.last_sent_dates.items():
                data[day] = date_obj.strftime('%Y-%m-%d') if date_obj else None
            
            with open(Config.DATES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved sent dates to {Config.DATES_FILE}")
        except Exception as e:
            logger.warning(f"Error saving sent dates: {e}")
    
    def load_onetime_messages(self) -> None:
        """Load one-time scheduled messages from JSON file"""
        try:
            if os.path.exists(Config.ONETIME_FILE):
                with open(Config.ONETIME_FILE, 'r', encoding='utf-8') as f:
                    self.onetime_messages = json.load(f)
                logger.info(f"Loaded {len(self.onetime_messages)} one-time messages")
            else:
                logger.info(f"No existing {Config.ONETIME_FILE} found, starting with empty list")
        except Exception as e:
            logger.warning(f"Error loading one-time messages: {e}")
            self.onetime_messages = []
    
    def save_onetime_messages(self) -> None:
        """Save one-time messages to JSON file"""
        try:
            with open(Config.ONETIME_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.onetime_messages, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.onetime_messages)} one-time messages")
        except Exception as e:
            logger.warning(f"Error saving one-time messages: {e}")
    
    def add_onetime_message(self, date_str: str, time_str: str, message: str, 
                           author: str, tag_everyone: bool = True) -> Tuple[bool, str]:
        """Add a new one-time message to the schedule"""
        try:
            # Validate date and time formats
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            target_time = datetime.strptime(time_str, '%H:%M').time()
            
            # Create message object
            onetime_msg = {
                'id': len(self.onetime_messages) + 1,
                'date': date_str,
                'time': time_str,
                'message': message,
                'author': author,
                'tag_everyone': tag_everyone,
                'created_at': datetime.now(Config.TZ).isoformat()
            }
            
            self.onetime_messages.append(onetime_msg)
            self.save_onetime_messages()
            
            tag_status = "avec @everyone" if tag_everyone else "sans @everyone"
            return True, f"Message programmé pour le {date_str} à {time_str} ({tag_status})"
        except ValueError as e:
            return False, f"Format de date/heure invalide: {e}"
        except Exception as e:
            return False, f"Erreur lors de l'ajout: {e}"
    
    def remove_onetime_message(self, message_id: int) -> None:
        """Remove a one-time message after it's been sent"""
        self.onetime_messages = [msg for msg in self.onetime_messages if msg['id'] != message_id]
        self.save_onetime_messages()
    
    @staticmethod
    def get_week_number(date: datetime) -> int:
        """Get ISO week number for determining even/odd weeks"""
        return date.isocalendar()[1]
    
    @staticmethod
    def is_even_week(date: datetime) -> bool:
        """Check if current week is even"""
        return ScheduledMessenger.get_week_number(date) % 2 == 0
    
    @staticmethod
    def french_to_english_day(french_day: str) -> str:
        """Convert French day name to English for dictionary lookup"""
        return DayMapping.FRENCH_TO_ENGLISH.get(french_day.lower(), french_day.lower())
    
    @staticmethod
    def get_current_day_french() -> str:
        """Get current day name in French"""
        now_paris = datetime.now(Config.TZ)
        english_day = now_paris.strftime('%A').lower()
        return DayMapping.ENGLISH_TO_FRENCH.get(english_day, english_day)
    
    def should_send_message(self, day_name_french: str, target_time: time) -> bool:
        """Check if we should send a message based on current time and last sent date"""
        now_paris = datetime.now(Config.TZ)
        today = now_paris.date()
        current_time = now_paris.time()
        
        # Convert French day name to English for dictionary lookup
        english_day = self.french_to_english_day(day_name_french)
        current_day_french = self.get_current_day_french()
        
        logger.debug(f"Checking message conditions: current_day={current_day_french}, "
                    f"target_day={day_name_french}, current_time={current_time}, target_time={target_time}")
        
        # Check if today matches the target day
        if current_day_french != day_name_french:
            return False
        
        # Check if current time is past target time
        if current_time < target_time:
            return False
            
        # Check if we already sent today (using English key)
        if self.last_sent_dates[english_day] == today:  
            return False
            
        return True
    
    def should_send_thursday_catchup(self) -> bool:
        """Check if we should send Thursday message in catch-up window"""
        now_paris = datetime.now(Config.TZ)
        current_day_french = self.get_current_day_french()
        
        # Must be Thursday and haven't sent today's message yet
        if (current_day_french == 'jeudi' and 
            self.last_sent_dates.get('thursday') != now_paris.date()):
            
            # Check if we're in the catch-up window (7:55 AM - 10:00 AM)
            is_normal_window = now_paris.time() >= Config.THURSDAY_TIME
            is_catch_up_window = now_paris.time() < Config.THURSDAY_CATCHUP_TIME
            
            return is_normal_window and is_catch_up_window
        
        return False
    
    async def send_scheduled_message(self, channel: discord.TextChannel, message: str, 
                                   day_name: str, is_catchup: bool = False) -> None:
        """Send a stylized message with embed and update last sent date"""
        try:
            now_paris = datetime.now(Config.TZ)
            
            # Get theme based on day and week
            theme = self._get_message_theme(day_name, now_paris)
            
            # Create embed
            embed = discord.Embed(
                title=f"{theme['icon']} {theme['title']}",
                description=message,
                color=theme['color'],
                timestamp=now_paris
            )
            
            # Add contextual information fields
            for field_name, field_value, inline in theme['info_fields']:
                if '{week_num}' in field_value:
                    week_num = self.get_week_number(now_paris)
                    field_value = field_value.format(week_num=week_num)
                embed.add_field(name=field_name, value=field_value, inline=inline)
            
            # Add catch-up note if applicable
            if is_catchup:
                embed.add_field(
                    name="⏰ Note", 
                    value="Message de rattrapage", 
                    inline=True
                )
            
            # Footer with timestamp
            embed.set_footer(
                text=f"Bot Planificateur • {now_paris.strftime('%H:%M')} Paris",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            # Send the embed with @everyone
            await channel.send(content="@everyone", embed=embed)
            
            # Update last sent date
            english_day = self.french_to_english_day(day_name)
            self.last_sent_dates[english_day] = now_paris.date()
            self.save_sent_dates()
            
            logger.info(f"Message {day_name} sent successfully: {theme['title']}")
            
        except Exception as e:
            logger.error(f"Error sending {day_name} message: {e}")
    
    def _get_message_theme(self, day_name: str, now_paris: datetime) -> Dict[str, Any]:
        """Get message theme based on day and week"""
        if day_name == 'thursday':
            if self.is_even_week(now_paris):
                return MessageThemes.THURSDAY_EVEN
            else:
                return MessageThemes.THURSDAY_ODD
        elif day_name == 'tuesday':
            return MessageThemes.TUESDAY
        elif day_name == 'sunday':
            return MessageThemes.SUNDAY
        else:
            # Default theme
            return {
                'color': discord.Color.blue(),
                'icon': '📅',
                'title': f'Message {day_name.capitalize()}',
                'info_fields': []
            }

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Create scheduler instance
scheduler = ScheduledMessenger(bot)

@bot.event
async def on_ready():
    """Bot ready event handler"""
    logger.info(f'Bot {bot.user} is ready!')
    logger.info('Scheduled messages:')
    logger.info('   - Thursday 7:55 AM (Even/Odd weeks)')
    logger.info('   - Tuesday 8:00 AM')
    logger.info('   - Sunday 6:00 PM')
    logger.info('   - One-time messages:')
    if scheduler.onetime_messages:
        for msg in scheduler.onetime_messages:
            logger.info(f'      - {msg["date"]} - {msg["time"]}')
    else:
        logger.info('No one-time messages scheduled')
    logger.info('All times are in Paris timezone')
    
    # Start the scheduler
    try:
        if not message_scheduler.is_running():
            message_scheduler.start()
            logger.info('Scheduler started successfully')
        else:
            logger.info('Scheduler already running')
    except Exception as e:
        logger.error(f'Failed to start scheduler: {e}')

@tasks.loop(minutes=1)
async def message_scheduler():
    """Check every minute if scheduled messages should be sent"""
    try:
        now_paris = datetime.now(Config.TZ)
        logger.debug(f"Scheduler check at {now_paris}")
        
        channel = bot.get_channel(Config.CHANNEL_ID)
        if not channel:
            logger.error(f"Channel with ID {Config.CHANNEL_ID} not found")
            return
        
        # Thursday messages with catch-up mechanism
        if scheduler.should_send_thursday_catchup():
            message = (Config.THURSDAY_EVEN_MESSAGE if scheduler.is_even_week(now_paris) 
                      else Config.THURSDAY_ODD_MESSAGE)
            week_type = "paire" if scheduler.is_even_week(now_paris) else "impaire"
            
            is_late = now_paris.time() > time(8, 10, 0)  # Consider late if after 8:10 AM
            if is_late:
                logger.info(f"Sending catch-up Thursday message at {now_paris.time()}")
            
            logger.info(f"Thursday (week {week_type}) - sending message")
            await scheduler.send_scheduled_message(channel, message, 'thursday', is_catchup=is_late)
        
        # Tuesday messages
        if scheduler.should_send_message('mardi', Config.TUESDAY_TIME):
            logger.info("Tuesday - sending message")
            await scheduler.send_scheduled_message(channel, Config.TUESDAY_MESSAGE, 'tuesday')
        
        # Sunday messages
        if scheduler.should_send_message('dimanche', Config.SUNDAY_TIME):
            logger.info("Sunday - sending message")
            await scheduler.send_scheduled_message(channel, Config.SUNDAY_MESSAGE, 'sunday')
        
        # Process one-time messages
        await _process_onetime_messages(channel, now_paris)
            
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")

async def _process_onetime_messages(channel: discord.TextChannel, now_paris: datetime):
    """Process and send one-time scheduled messages"""
    current_date = now_paris.date()
    current_time = now_paris.time()
    
    for msg in scheduler.onetime_messages[:]:  # Use slice to avoid modification during iteration
        try:
            target_date = datetime.strptime(msg['date'], '%Y-%m-%d').date()
            target_time = datetime.strptime(msg['time'], '%H:%M').time()
            
            # Check if it's time to send this message
            if (current_date == target_date and 
                current_time.hour == target_time.hour and 
                current_time.minute == target_time.minute):
                
                # Create embed for one-time message
                embed = discord.Embed(
                    title="📅 Message Programmé",
                    description=msg['message'],
                    color=discord.Color.gold(),
                    timestamp=now_paris
                )
                embed.add_field(name="👤 Programmé par", value=msg['author'], inline=True)
                embed.add_field(name="📅 Date/Heure", value=f"{msg['date']} à {msg['time']}", inline=True)
                
                # Handle @everyone tagging
                tag_everyone = msg.get('tag_everyone', True)
                if tag_everyone:
                    embed.add_field(name="🔔 Notification", value="@everyone", inline=True)
                    embed.set_footer(text="Message unique avec notification • Bot Planificateur")
                    content = "@everyone"
                else:
                    embed.add_field(name="🔇 Notification", value="Silencieux", inline=True)
                    embed.set_footer(text="Message unique silencieux • Bot Planificateur")
                    content = None
                
                await channel.send(content=content, embed=embed)
                logger.info(f"One-time message sent (ID: {msg['id']}): {msg['message'][:50]}...")
                
                # Remove the message after sending
                scheduler.remove_onetime_message(msg['id'])
                
        except Exception as e:
            logger.warning(f"Error processing one-time message {msg.get('id', 'unknown')}: {e}")

@message_scheduler.before_loop
async def before_scheduler():
    """Wait for bot to be ready before starting scheduler"""
    await bot.wait_until_ready()

# Bot Commands
@bot.command(name='status')
@commands.cooldown(1, 10, commands.BucketType.user)
async def status_command(ctx):
    """Check bot status and upcoming scheduled messages"""
    now_paris = datetime.now(Config.TZ)
    
    # French translations for days and months
    days_fr = DayMapping.FRENCH_DISPLAY
    months_fr = {
        'January': 'Janvier', 'February': 'Février', 'March': 'Mars', 'April': 'Avril',
        'May': 'Mai', 'June': 'Juin', 'July': 'Juillet', 'August': 'Août',
        'September': 'Septembre', 'October': 'Octobre', 'November': 'Novembre', 'December': 'Décembre'
    }
    
    embed = discord.Embed(
        title="🤖 Statut du Bot", 
        description="*Système de planification automatique des messages*",
        color=discord.Color.from_rgb(87, 242, 135),  # Vert stylé
        timestamp=now_paris
    )
    
    # Format date in French
    date_str = now_paris.strftime("%A, %B %d, %Y at %H:%M:%S")
    for eng, fr in days_fr.items():
        date_str = date_str.replace(eng, fr)
    for eng, fr in months_fr.items():
        date_str = date_str.replace(eng, fr)
    
    embed.add_field(
        name="⏰ Heure Actuelle (Paris)", 
        value=date_str,
        inline=False
    )
    
    week_num = scheduler.get_week_number(now_paris)
    week_type = "Paire" if scheduler.is_even_week(now_paris) else "Impaire"
    embed.add_field(
        name="📊 Info Semaine", 
        value=f"Semaine {week_num} ({week_type})",
        inline=True
    )
    
    # Last sent dates
    day_names_fr = {'thursday': 'Jeudi', 'tuesday': 'Mardi', 'sunday': 'Dimanche'}
    last_sent_info = []
    for day, date in scheduler.last_sent_dates.items():
        day_fr = day_names_fr.get(day, day.capitalize())
        if date:
            last_sent_info.append(f"{day_fr}: {date.strftime('%d/%m/%Y')}")
        else:
            last_sent_info.append(f"{day_fr}: Jamais")
    
    embed.add_field(
        name="📨 Derniers Envois", 
        value="\n".join(last_sent_info),
        inline=True
    )
    
    embed.add_field(
        name="📅 Horaires", 
        value="🌅 Jeudi: 07:55\n🔥 Mardi: 08:00\n🌅 Dimanche: 18:00",
        inline=True
    )
    
    # Ajouter une image thumbnail et footer stylisé
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
    embed.set_footer(
        text=f"Bot actif depuis le démarrage • Heure Paris: {now_paris.strftime('%H:%M:%S')}",
        icon_url="https://cdn.discordapp.com/embed/avatars/1.png"
    )
    
    await ctx.send(embed=embed)

@bot.command(name='test_message')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def test_message(ctx, day: str = None):
    """Test sending a scheduled message manually (with @everyone)"""
    if not day:
        await ctx.send("Usage : `!test_message <jeudi/mardi/dimanche>`")
        return
    
    day = day.lower()
    # Accept both French and English day names
    day_mapping = {
        'jeudi': 'thursday', 'thursday': 'thursday',
        'mardi': 'tuesday', 'tuesday': 'tuesday', 
        'dimanche': 'sunday', 'sunday': 'sunday'
    }
    
    if day not in day_mapping:
        await ctx.send("Jour invalide ! Utilisez : jeudi, mardi, ou dimanche")
        return
    
    day_en = day_mapping[day]
    
    channel = bot.get_channel(Config.CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Canal cible introuvable (ID : {Config.CHANNEL_ID})")
        return
    
    if day_en == 'thursday':
        now_paris = datetime.now(Config.TZ)
        if scheduler.is_even_week(now_paris):
            message = Config.THURSDAY_EVEN_MESSAGE
            test_color = discord.Color.purple()
        else:
            message = Config.THURSDAY_ODD_MESSAGE
            test_color = discord.Color.red()
    elif day_en == 'tuesday':
        message = Config.TUESDAY_MESSAGE
        test_color = discord.Color.orange()
    else:  # sunday
        message = Config.SUNDAY_MESSAGE
        test_color = discord.Color.blue()
    
    try:
        # Use the scheduler's send method for consistency, but mark as test
        await scheduler.send_scheduled_message(channel, f"🧪 **TEST** - {message}", day_en)
        await ctx.send(f"✅ Test message sent with @everyone to {channel.mention}")
    except Exception as e:
        await ctx.send(f"❌ Error sending test message: {e}")

@bot.command(name='test_silent')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def test_silent(ctx, day: str = None):
    """Tester l'envoi d'un message programmé silencieusement (sans @everyone)"""
    if not day:
        await ctx.send("Usage : `!test_silent <jeudi/mardi/dimanche>`")
        return
    
    day = day.lower()
    # Accept both French and English day names
    day_mapping = {
        'jeudi': 'thursday', 'thursday': 'thursday',
        'mardi': 'tuesday', 'tuesday': 'tuesday', 
        'dimanche': 'sunday', 'sunday': 'sunday'
    }
    
    if day not in day_mapping:
        await ctx.send("Jour invalide ! Utilisez : jeudi, mardi, ou dimanche")
        return
    
    day_en = day_mapping[day]
    
    channel = bot.get_channel(Config.CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Canal cible introuvable (ID : {Config.CHANNEL_ID})")
        return
    
    if day_en == 'thursday':
        now_paris = datetime.now(Config.TZ)
        if scheduler.is_even_week(now_paris):
            message = Config.THURSDAY_EVEN_MESSAGE
            test_color = discord.Color.purple()
        else:
            message = Config.THURSDAY_ODD_MESSAGE
            test_color = discord.Color.red()
    elif day_en == 'tuesday':
        message = Config.TUESDAY_MESSAGE
        test_color = discord.Color.orange()
    else:  # sunday
        message = Config.SUNDAY_MESSAGE
        test_color = discord.Color.blue()
    
    try:
        # Créer un embed de test silencieux (couleur plus pâle)
        darker_color = discord.Color.from_rgb(
            max(0, test_color.r - 80),
            max(0, test_color.g - 80), 
            max(0, test_color.b - 80)
        )
        
        now_paris = datetime.now(Config.TZ)
        embed = discord.Embed(
            title="🔇 TEST SILENCIEUX",
            description=f"**Aperçu du message {day_en.capitalize()} :**\n\n{message}",
            color=darker_color,
            timestamp=now_paris
        )
        
        if day_en == 'thursday':
            week_type = "Paire" if scheduler.is_even_week(now_paris) else "Impaire"
            embed.add_field(name="📊 Type", value=f"Semaine {week_type}", inline=True)
        
        embed.add_field(name="🔇 Note", value="Test silencieux (sans @everyone)", inline=True)
        embed.set_footer(text=f"Test silencieux demandé par {ctx.author.display_name}")
        
        # Envoyer sans @everyone
        await channel.send(embed=embed)
        await ctx.send(f"✅ Message de test silencieux envoyé dans {channel.mention}")
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de l'envoi du message de test silencieux : {e}")

@bot.command(name='schedule')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def schedule_onetime_message(ctx, date: str = None, time: str = None, notification: str = None, *, message: str = None):
    """Programmer un message unique à une date/heure précise
    Usage: !schedule YYYY-MM-DD HH:MM [everyone/silent] Votre message ici
    Example: !schedule 2025-06-15 14:30 everyone Rappel important pour demain !
    Example: !schedule 2025-06-15 14:30 silent Message discret
    """
    if not date or not time or not notification or not message:
        embed = discord.Embed(
            title="❌ Format Incorrect",
            description="**Usage:** `!schedule YYYY-MM-DD HH:MM [everyone/silent] Votre message`",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📝 Exemples", 
            value="`!schedule 2025-06-15 14:30 everyone Rappel important !`\n`!schedule 2025-06-15 14:30 silent Message discret`",
            inline=False
        )
        embed.add_field(
            name="📋 Format", 
            value="• Date: `YYYY-MM-DD` (ex: 2025-06-15)\n• Heure: `HH:MM` (ex: 14:30)\n• Notification: `everyone` ou `silent`\n• Message: Texte libre",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    # Parse notification setting
    if notification.lower() not in ['everyone', 'silent']:
        await ctx.send("❌ Notification doit être `everyone` ou `silent` !")
        return
    
    tag_everyone = notification.lower() == 'everyone'
    
    # Validate date is in the future
    try:
        target_datetime = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
        target_paris = Config.TZ.localize(target_datetime)
        now_paris = datetime.now(Config.TZ)
        
        if target_paris <= now_paris:
            await ctx.send("❌ La date/heure doit être dans le futur !")
            return
    except ValueError:
        await ctx.send("❌ Format de date/heure invalide ! Utilisez YYYY-MM-DD HH:MM")
        return
    
    # Add the message to scheduler
    success, result_msg = scheduler.add_onetime_message(date, time, message, ctx.author.display_name, tag_everyone)
    
    if success:
        embed = discord.Embed(
            title="✅ Message Programmé",
            description=f"Votre message sera envoyé le **{date}** à **{time}** (heure de Paris)",
            color=discord.Color.green(),
            timestamp=datetime.now(Config.TZ)
        )
        embed.add_field(
            name="📝 Message", 
            value=f"```{message}```",
            inline=False
        )
        embed.add_field(
            name="👤 Programmé par", 
            value=ctx.author.display_name,
            inline=True
        )
        
        # Calculate time until message
        time_until = target_paris - now_paris
        days = time_until.days
        hours, remainder = divmod(time_until.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        time_str = []
        if days > 0:
            time_str.append(f"{days} jour(s)")
        if hours > 0:
            time_str.append(f"{hours} heure(s)")
        if minutes > 0:
            time_str.append(f"{minutes} minute(s)")
        
        embed.add_field(
            name="⏰ Dans", 
            value=" ".join(time_str) if time_str else "moins d'une minute",
            inline=True
        )
        
        notification_text = "avec @everyone" if tag_everyone else "sans notification @everyone"
        embed.set_footer(text=f"Le message sera envoyé {notification_text}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {result_msg}")

@bot.command(name='list_scheduled')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def list_scheduled_messages(ctx):
    """Lister tous les messages programmés"""
    if not scheduler.onetime_messages:
        embed = discord.Embed(
            title="📋 Messages Programmés",
            description="Aucun message programmé pour le moment.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📋 Messages Programmés",
        description=f"**{len(scheduler.onetime_messages)}** message(s) en attente",
        color=discord.Color.blue(),
        timestamp=datetime.now(Config.TZ)
    )
    
    now_paris = datetime.now(Config.TZ)
    
    for msg in scheduler.onetime_messages:
        try:
            target_datetime = datetime.strptime(f"{msg['date']} {msg['time']}", '%Y-%m-%d %H:%M')
            target_paris = Config.TZ.localize(target_datetime)
            
            # Calculate time until message
            time_until = target_paris - now_paris
            if time_until.total_seconds() > 0:
                days = time_until.days
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                time_str = []
                if days > 0:
                    time_str.append(f"{days}j")
                if hours > 0:
                    time_str.append(f"{hours}h")
                if minutes > 0:
                    time_str.append(f"{minutes}m")
                
                time_display = " ".join(time_str) if time_str else "<1m"
            else:
                time_display = "En retard"
            
            tag_status = "🔔 @everyone" if msg.get('tag_everyone', True) else "🔇 Silencieux"
            embed.add_field(
                name=f"🔹 ID #{msg['id']} - {msg['date']} à {msg['time']} ({tag_status})",
                value=f"**Message:** {msg['message'][:100]}{'...' if len(msg['message']) > 100 else ''}\n"
                      f"**Par:** {msg['author']} • **Dans:** {time_display}",
                inline=False
            )
        except Exception as e:
            embed.add_field(
                name=f"❌ ID #{msg.get('id', '?')} - Erreur",
                value=f"Format invalide: {e}",
                inline=False
            )
    
    embed.set_footer(text="Utilisez !cancel_scheduled <ID> pour annuler un message")
    await ctx.send(embed=embed)

@bot.command(name='cancel_scheduled')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)  
async def cancel_scheduled_message(ctx, message_id: int = None):
    """Annuler un message programmé par son ID"""
    if message_id is None:
        await ctx.send("❌ Veuillez spécifier l'ID du message à annuler.\nUtilisez `!list_scheduled` pour voir les IDs.")
        return
    
    # Find the message
    msg_to_cancel = None
    for msg in scheduler.onetime_messages:
        if msg['id'] == message_id:
            msg_to_cancel = msg
            break
    
    if not msg_to_cancel:
        await ctx.send(f"❌ Aucun message programmé trouvé avec l'ID #{message_id}")
        return
    
    # Remove the message
    scheduler.remove_onetime_message(message_id)
    
    embed = discord.Embed(
        title="🗑️ Message Annulé",
        description=f"Le message #{message_id} a été supprimé de la programmation.",
        color=discord.Color.orange(),
        timestamp=datetime.now(Config.TZ)
    )
    embed.add_field(
        name="📝 Message annulé", 
        value=f"```{msg_to_cancel['message']}```",
        inline=False
    )
    embed.add_field(
        name="📅 Était prévu pour", 
        value=f"{msg_to_cancel['date']} à {msg_to_cancel['time']}",
        inline=True
    )
    embed.add_field(
        name="👤 Programmé par", 
        value=msg_to_cancel['author'],
        inline=True
    )
    
    tag_status = "Avec @everyone" if msg_to_cancel.get('tag_everyone', True) else "Silencieux"
    embed.add_field(
        name="🔔 Type", 
        value=tag_status,
        inline=True
    )
    embed.set_footer(text=f"Annulé par {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='reset_dates')
@commands.cooldown(1, 10, commands.BucketType.user)
@commands.has_permissions(administrator=True)
async def reset_dates_command(ctx):
    """Réinitialiser les dates d'envoi stockées (Admin seulement)"""
    try:
        scheduler.last_sent_dates = {
            'thursday': None,
            'tuesday': None, 
            'sunday': None
        }
        scheduler.save_sent_dates()
        
        embed = discord.Embed(
            title="🔄 Réinitialisation Effectuée", 
            description="Les dates d'envoi ont été réinitialisées.\nTous les messages pourront être envoyés à nouveau.",
            color=discord.Color.yellow(),
            timestamp=datetime.now(Config.TZ)
        )
        embed.add_field(name="⚠️ Attention", value="Les messages automatiques vont reprendre normalement", inline=False)
        embed.set_footer(text=f"Réinitialisé par {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la réinitialisation : {e}")

@bot.command(name='help_bot')
@commands.cooldown(1, 10, commands.BucketType.user)
async def help_command(ctx):
    """Afficher l'aide du bot"""
    embed = discord.Embed(
        title="🤖 Aide - Bot Planificateur Discord", 
        description="*Votre assistant automatique pour les rappels de jeu*",
        color=discord.Color.from_rgb(114, 137, 218),  # Bleu Discord stylé
    )
    
    embed.add_field(
        name="📅 Programmation Automatique",
        value="⚡ **Jeudi 07:55** - Messages semaines paires/impaires\n🎯 **Mardi 08:00** - Message hebdomadaire\n🏆 **Dimanche 18:00** - Message hebdomadaire",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Commandes Générales",
        value="```\n!status          - Vérifier le statut du bot\n!help_bot        - Afficher cette aide\n```",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Commandes Admin - Tests",
        value="```\n!test_message    - Tester un message avec @everyone\n!test_silent     - Tester un message silencieux\n!reset_dates     - Réinitialiser les dates d'envoi\n```",
        inline=False
    )
    
    embed.add_field(
        name="📅 Commandes Admin - Programmation",
        value="```\n!schedule        - Programmer un message unique\n!list_scheduled  - Lister les messages programmés\n!cancel_scheduled- Annuler un message programmé\n```",
        inline=False
    )
    
    embed.add_field(
        name="🕐 Fuseau Horaire",
        value=f"🌍 Tous les horaires sont en **{os.getenv('TIMEZONE', 'Europe/Paris')}**\n*Le bot gère automatiquement les changements d'heure*",
        inline=False
    )
    
    # Footer et thumbnail stylisés
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/2.png")
    embed.set_footer(
        text="Bot Planificateur • Développé pour votre serveur",
        icon_url="https://cdn.discordapp.com/embed/avatars/3.png"
    )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing the command.")


"""
# Configure encoding for Windows
import sys
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    except:
        pass
"""
import requests
import threading
import time as time_module

def auto_ping():
    while True:
        try:
            requests.get("https://alert-bot-foe.onrender.com") #ton adresse web
            print("✅ Auto-ping envoyé.")
        except Exception as e:
            print(f"❌ Erreur auto-ping : {e}")
        time_module.sleep(300) 
    
keep_alive()
threading.Thread(target=auto_ping, daemon=True).start()
# Validate required environment variables
if not Config.TOKEN:
    logger.error("DISCORD_TOKEN not found in environment variables!")
    logger.error("Please create a .env file based on config.env.example")
    exit(1)

if not Config.CHANNEL_ID:
    logger.error("CHANNEL_ID not found in environment variables!")
    logger.error("Please create a .env file based on config.env.example")
    exit(1)

logger.info("Starting Discord Bot...")
try:
    bot.run(Config.TOKEN)
except Exception as e:
    logger.error(f"Failed to start bot: {e}")
    exit(1)