import json
import os
import logging
import traceback
import re
import operator
import random
import requests
from bs4 import BeautifulSoup

from config import TOKEN, DIR, DUPLICATE_REG_TEXT, TOMORROWMAN_CHAT_ID, GO_TEXT, BEG_TEXT, ADMIN_ID, CHANNEL_ID
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, BaseFilter, CallbackQueryHandler
from emoji import emojize

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# service functions

def loadStats():
    with open(DIR + 'STATS.json', 'r', encoding='utf-8') as fl:
        STATS = json.load(fl)
    return STATS

def updateStats(STATS):
    with open(DIR + 'STATS.json', 'w', encoding='utf-8') as fl:
        json.dump(STATS, fl, indent=2, ensure_ascii=False)

def loadLastGameDate():
    with open(DIR + 'LASTGAMEDATE.json', 'r', encoding='utf-8') as fl:
        LASTGAMEDATE = json.load(fl)
    return LASTGAMEDATE

def updateLastGameDate(LASTGAMEDATE):
    with open(DIR + 'LASTGAMEDATE.json', 'w', encoding='utf-8') as fl:
        json.dump(LASTGAMEDATE, fl, indent=2, ensure_ascii=False)

def isAdmin(id):
    return id in ADMIN_ID
# end service functions

# initialize

BOT_USERNAME = 'PUT BOT NAME HERE'

KRAKEN_API_LINK = 'https://api.kraken.com/0/public/Ticker?pair='

STATS = loadStats()
LASTGAMEDATE = loadLastGameDate()

ls = []

# define custom filters

class regFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.replace(BOT_USERNAME, '')
        return txt == '/reg' and message.chat_id in TOMORROWMAN_CHAT_ID and message.forward_from == None

reg_filter = regFilter()

class goFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.replace(BOT_USERNAME, '')
        return txt == '/go' and message.chat_id in TOMORROWMAN_CHAT_ID and message.forward_from == None
    
go_filter = goFilter()

class statFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.replace(BOT_USERNAME, '')
        #txt = txt.replace('@enchanted_warrior_bot', '')
        return txt == '/st' and message.chat_id in TOMORROWMAN_CHAT_ID and message.forward_from == None

stat_filter = statFilter()

class removeFilter(BaseFilter):
    def filter(self, message):
        return len(re.findall(r'/rm (\d+)', message.text)) != 0

remove_filter = removeFilter()

class begFilter(BaseFilter):
    def filter(self, message):
        return len(re.findall(r'^/beg (-?\d+)$', message.text)) != 0

beg_filter = begFilter()

class newsFilter(BaseFilter):
    def filter(self, message):
        return len(re.findall(r'^/news (-?\d+)$', message.text)) != 0

news_filter = newsFilter()

class priceFilter(BaseFilter):
    def filter(self, message):
        return len(re.findall(r'^/prc[_ ]([a-zA-Z]{2,4})([a-zA-Z]{3})$', message.text)) != 0

price_filter = priceFilter()

def reg(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    username = update.message.from_user.username
    STATS = loadStats()
    #msg = update.message.text
    try:
        if str(user_id) not in STATS:
            STATS[user_id] = {}
            STATS[user_id]['first_name'] = user_first_name
            STATS[user_id]['last_name'] = (user_last_name if user_last_name != None else '')
            STATS[user_id]['username'] = (username if username != None else '')
            STATS[user_id]['count'] = 0
            STATS[user_id]['winner'] = 0
            updateStats(STATS)
            context.bot.send_message(chat_id, 'Welcome to the random!')
        else:
            context.bot.send_message(chat_id, random.choice(DUPLICATE_REG_TEXT))
    except Exception:
        logging.error(traceback.format_exc())

def sendRandomPhrases(context):
    job = context.job
    global ls
    if len(ls) == 0:
        job.schedule_removal()
    else:
        txt = random.choice(ls)
        context.bot.send_message(chat_id=context.job.context, text=txt)
        ls.remove(txt)

def defineWinner(context):
    STATS = loadStats()
    for user in STATS:
        STATS[user]['winner'] = 0
    winner = random.choice(list(STATS.keys()))
    STATS[winner]['count'] += 1
    STATS[winner]['winner'] = 1
    updateStats(STATS)
    if STATS[winner]['username'] == '':
        winner_text = '<a href=\'tg://user?id='+str(winner)+'\'>'+STATS[winner]['first_name']+'</a>'
    else:
        winner_text = '@'+STATS[winner]['username']
    a = context.bot.send_message(chat_id=context.job.context, text='And the <b>winner</b> is... ' + winner_text, parse_mode='HTML')
    context.bot.pin_chat_message(chat_id=context.job.context, message_id=a.message_id)

def go(update, context):
    global ls
    ls = GO_TEXT.copy()
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    #STATS = loadStats()
    try:
        if str(user_id) not in loadStats():
            context.bot.send_message(chat_id, 'In order to start the game, please register: /reg.')
        else:
            dt = str(update.message.date)
            currentGameDate = dt[0:10]
            if currentGameDate > LASTGAMEDATE[0]:
                context.bot.send_message(chat_id, 'Go go GO!')
                context.job_queue.run_repeating(sendRandomPhrases, 1.4, context=chat_id)
                context.job_queue.run_once(defineWinner, 1.4*len(GO_TEXT)+1.8, context=chat_id)
                LASTGAMEDATE[0] = currentGameDate
                updateLastGameDate(LASTGAMEDATE)
            else:
                winner = ''
                STATS = loadStats()
                for user_id in STATS:
                    if STATS[user_id]['winner'] == 1:
                        winner = user_id
                if winner == '':
                    context.bot.send_message(chat_id, 'You have already played, but now you try to delete the statistics? Not a good way.')
                else:
                    context.bot.send_message(chat_id, 'Today we have played already. The winner was <b>'+ (STATS[winner]['username'] if STATS[winner]['username'] != '' else STATS[winner]['first_name']) +'</b>. Come tomorrow.', parse_mode='HTML')
    except Exception:
        logging.error(traceback.format_exc())

def stat(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    STATS = loadStats()
    short = {}
    try:
        for user_id in STATS:
            short[user_id] = STATS[user_id]['count']
        sorted_short = sorted(short.items(), key = operator.itemgetter(1), reverse=True)
        text = 'Score:\n'
        count = 1
        for user_id in STATS:
            text = text + str(count) + '. ' + (STATS[str(sorted_short[count-1][0])]['username'] if STATS[str(sorted_short[count-1][0])]['username'] != '' else STATS[str(sorted_short[count-1][0])]['first_name']) + ' - <code>' + str(STATS[str(sorted_short[count-1][0])]['count']) + '</code>\n'
            count = count+1
        context.bot.send_message(chat_id, text, parse_mode = 'HTML')
    except Exception:
        logging.error(traceback.format_exc())

def begJob(context):
    #job = context.job
    txt = random.choice(BEG_TEXT)
    context.bot.send_message(chat_id=context.job.context, text=txt)

def beg(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    msg = update.message.text
    intrvl = re.search(r'^/beg (-?\d+)$', msg).group(1)
    try:
        if isAdmin(user_id):
            if int(intrvl) >= 0:
                print('starting')
                context.job_queue.run_repeating(begJob, interval=int(intrvl), first=0, context=chat_id, name='Beg')
                print(context.job_queue.jobs())
            elif int(intrvl) < 0:
                print('stopping')
                context.job_queue.jobs()[0].schedule_removal()
                print(context.job_queue.jobs())
            else:
                pass
    except Exception:
        logging.error(traceback.format_exc())

def fetchNews(context):
    yandex = requests.get('https://yandex.ru')
    yandex_all = BeautifulSoup(yandex.text, 'html.parser')
    yandex_a_tags = yandex_all.find_all('a')
    yandex_links = []
    for i in range(len(yandex_a_tags)):
        if 'https://yandex.ru/news/story/' in yandex_a_tags[i].get('href'):
            yandex_links.append(yandex_a_tags[i].get('href'))
    for i in range(len(yandex_links)):
        yandex_links[i] = yandex_links[i][:yandex_links[i].find('?')]
    yandex_random_news = random.choice(yandex_links)
    context.bot.send_message(chat_id=context.job.context, text=yandex_random_news)

def sendNews(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    msg = update.message.text
    intrvl = re.search(r'^/news (-?\d+)$', msg).group(1)
    try:
        if isAdmin(user_id):
            if int(intrvl) >= 0:
                print('starting')
                context.job_queue.run_repeating(fetchNews, interval=int(intrvl), first=0, context=chat_id, name='News')
                print(context.job_queue.jobs())
            elif int(intrvl) < 0:
                print('stopping')
                context.job_queue.jobs()[0].schedule_removal()
                print(context.job_queue.jobs())
            else:
                pass
    except Exception:
        logging.error(traceback.format_exc())


def resetDate(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    if isAdmin(user_id):
        LASTGAMEDATE[0] = '1990-01-01'
        updateLastGameDate(LASTGAMEDATE)
        context.bot.send_message(chat_id, 'Date set to default.')

def resetStats(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    if isAdmin(user_id):
        STATS = loadStats()
        for user_id in STATS:
            STATS[user_id]['count'] = 0
            STATS[user_id]['winner'] = 0
        updateStats(STATS)
        context.bot.send_message(chat_id, 'Statistics set to 0.')

def removePlayer(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    msg = update.message.text
    id_to_delete = re.search(r'/rm (\d+)', msg).group(1)
    if isAdmin(user_id):
        STATS = loadStats()
        if id_to_delete not in STATS:
            context.bot.send_message(chat_id, 'There is no such player in the list.')
        else:
            del STATS[id_to_delete]
            updateStats(STATS)
            context.bot.send_message(chat_id, 'Deleted.')

def listPlayers(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    if isAdmin(user_id):
        STATS = loadStats()
        text = 'List of the players:\n'
        for user in STATS:
            text = text + '- ' + user + ' ' + STATS[user]['username'] + '\n'
        context.bot.send_message(chat_id, text)

def getCrypto(update, context):
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    msg = update.message.text
    try:
        crypto = re.search(r'^/prc[_ ]([a-zA-Z]{2,4})([a-zA-Z]{3})$', msg).group(1).upper()
        fiat = re.search(r'^/prc[_ ]([a-zA-Z]{2,4})([a-zA-Z]{3})$', msg).group(2).upper()
        rawTickerData = requests.get(KRAKEN_API_LINK+crypto+fiat)
        tickerData = rawTickerData.json()
        if len(tickerData['error']) == 0:
            currentPrice = tickerData['result'][list(tickerData['result'].keys())[0]]['c'][0]
            context.bot.send_message(chat_id, text = '1 '+crypto+' = <code>'+currentPrice+'</code> '+fiat, parse_mode = 'HTML')
        else:
            context.bot.send_message(chat_id, text = '<i>'+tickerData['error'][0]+'</i>', parse_mode = 'HTML')
    except Exception:
        logging.error(traceback.format_exc())

def sendToChannel(update, context):
    chat_id = update.effective_chat.id
    if update.message.reply_to_message is None:
        context.bot.send_message(chat_id, 'You have to reply to a message in order to send it to the channel.')
    else:
        replied_info = update.message.reply_to_message
        try:
            #context.bot.forward_message(chat_id = CHANNEL_ID, from_chat_id = chat_id, message_id = replied_info.message_id)
            context.bot.send_message(chat_id = CHANNEL_ID, text = replied_info.text, parse_mode = 'HTML')
            #context.bot.copy_message(chat_id = CHANNEL_ID, from_chat_id = chat_id, message_id = replied_info.message_id)
        except Exception:
            logging.error(traceback.format_exc())

def main():

    updater = Updater(token=TOKEN, use_context = True)
    dispatcher = updater.dispatcher

    go_handler = MessageHandler(go_filter, go)
    dispatcher.add_handler(go_handler)

    reg_handler = MessageHandler(reg_filter, reg)
    dispatcher.add_handler(reg_handler)

    stat_handler = MessageHandler(stat_filter, stat)
    dispatcher.add_handler(stat_handler)

    beg_handler = MessageHandler(beg_filter, beg)
    dispatcher.add_handler(beg_handler)

    news_handler = MessageHandler(news_filter, sendNews)
    dispatcher.add_handler(news_handler)

    reset_date_handler = CommandHandler('rsd', resetDate)
    dispatcher.add_handler(reset_date_handler)

    reset_stats_handler = CommandHandler('rss', resetStats)
    dispatcher.add_handler(reset_stats_handler)

    remove_player_handler = MessageHandler(remove_filter, removePlayer)
    dispatcher.add_handler(remove_player_handler)

    list_handler = CommandHandler('ls', listPlayers)
    dispatcher.add_handler(list_handler)

    price_handler = MessageHandler(price_filter, getCrypto)
    dispatcher.add_handler(price_handler)

    send_to_channel = CommandHandler('send', sendToChannel)
    dispatcher.add_handler(send_to_channel)

    updater.start_polling()
    
    updater.idle()


if __name__ == '__main__':
    main()
