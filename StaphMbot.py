#! /usr/bin/env python3

import sqldb
import urllib.error as ue
import urllib.request as ur
import urllib.parse as up
import json
import datetime
import time
import sys
import os

__version__ = '0.1'
__doc__ = '''StaphMB - A Telegram Group Management Bot infected by _S. aureus_

Synopsis:\n\tStaphMbot.py sqlite.db API-Key

Version:\n\t'''+str(__version__)

class APIError(Exception):
    def __init__(self,module,info):
        self.module = module
        self.info = info
    def __str__(self):
        return 'Telegram Bot '+self.module+' Exception: '+self.info
    def __repr__(self):
        return '<TGBot Exception="'+self.module+'" Info="'+self.info+'" />'

class stdOut():
    def __init__(self,fName=None):
        self.fh = None if fName is None else open(fName,'a',1)
    def writeln(self,data):
        if self.fh is None:
            print('['+str(int(time.time()))+'] '+str(data))
        else:
            self.fh.write('['+str(int(time.time()))+'] '+str(data)+'\n')

class tgapi:
    __doc__ = 'tgapi - Telegram Chat Bot HTTPS API Wrapper'

    def __init__(self,apikey,logger=None,maxRetry=5):
        self.logOut = stdOut() if logger is None else logger
        self.target = 'https://api.telegram.org/bot'+apikey+'/'
        self.retry = maxRetry
        self.info = self.query('getMe')
        if self.info is None:
            raise APIError('API', 'Initialization Self-test Failed')
        self.logOut.writeln("Bot "+self.info["username"]+" connected to the Telegram API.")

    def query(self,met,parameter=None,retry=None):
        req = ur.Request(self.target+met,method='POST')
        req.add_header('User-Agent','StaphMbot/0.1 (+https://github.com/StephDC/StaphMbot)')
        if parameter is not None:
            req.add_header('Content-Type','application/json')
            req.data = json.dumps(parameter).encode('UTF-8')
        #            print(req.data.decode('UTF-8'))
        retryCount = 0
        maxRetry = retry if retry is not None else self.retry
        failed = True
        while failed:
            try:
                resp = ur.urlopen(req)
            except ue.HTTPError:
                if retryCount >= maxRetry:
                    raise APIError('API','Query HTTP Error')
            except ue.URLError:
                if retryCount >= maxRetry:
                    raise APIError('API','Query DNS Error')
            else:
                failed = False
                break
            self.logOut.writeln("Query failed. Try again in 5 sec.")
            self.logOut.writeln("Failed Request:\nMethod: "+met+"\nParameters: "+str(parameter))
            time.sleep(5)
            retryCount += 1
        data = json.loads(resp.read().decode('UTF-8'))
        #print(data)
        return data['result'] if data['ok'] else None
    
    def sendMessage(self,target,text,misc={}):
        misc['text'] = text
        misc['chat_id'] = target
        data = self.query('sendMessage',misc)
        if data and data['text'] == text:
            return data['message_id']
        else:
            return False

# A few output formatting functions
class l10n:
    def __init__(self,lang = "en_US"):
        self.lang = lang
        print("This class is not ready to be instantiated now. Please don't instantiate and directly use the functions")
    warnSuccess = lambda x,c: '警告成功。該用戶現在共有 '+x+' 個警告。'+(('\n'+c) if (c and c != "None") else '')
    delWarnSuccess = lambda t,a,r,c: '該條訊息曾於 '+t+' 被 '+a+' 以理由「 '+r+' 」警告過。警告現已取消。該用戶現有 '+c+' 個警告。如該用戶已因警告遭致處分，請管理員亦一同處置。'
    warnedFail = lambda t,a,r: '抱歉，該條訊息已於 '+t+' 被 '+a+' 以理由「 '+r+' 」警告過。'
    epochToISO = lambda x: datetime.datetime.fromtimestamp(x).isoformat()
    notifyWarn = lambda i,t,u,uid,a,c,m,r: "ID: "+i+"\nTime: "+t+"\nUser "+u+" ("+uid+") warned by "+a+' with reason:\n'+r+'\nCurrent Warn #'+c+'\nMessage:\n'+(m if m else '<Multimedia Message>')
    notifyDelwarn = lambda i,t,u,uid,a,c,m,r: "ID: "+i+'\nTime: '+t+"\n"+a+" cancelled a warning for user "+u+" ("+uid+") with reason:\n"+r+'\nCurrent Warn #:'+c+'\nMessage:\n' + (m if m else '<Multimedia Message>')
    notifyG11 = lambda t,u,uid,a,m: "Time: "+t+"\nUser "+u+" ("+uid+") killed by "+a+' with reason: #G11\nMessage:\n'+getMsgText(m)
    notifyPunish = lambda p,t,u,uid: "User "+u+" ("+uid+") has been "+p+" till "+t+"."
    notifyPunishFail = lambda p,t,u,uid: "User "+u+" ("+uid+") need to be "+p+" till "+t+", but the operation failed."

def initiateDB(fName,outdev):
    try:
        conf = sqldb.sqliteDB(fName,'config')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted configuration table')
    if conf.getItem('dbver','value') != '1.2':
        raise APIError('DB','Database schema version is incompatible')
    try:
        group = sqldb.sqliteDB(conf.db,'group')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted group table')
    try:
        warn = sqldb.sqliteDB(conf.db,'warn')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted warn table')
    outdev.writeln('DB File '+fName+' loaded.')
    return (conf,group,warn)

def addGroup(gid,db,outdev):
    if not db[1].hasItem(str(gid)):
        db[1].addItem([str(gid)]+[str(i) for i in db[1].data.execute('select * from "group" where header="default"').fetchone()[1:]])
        outdev.writeln('I\'ve been added to a new group '+str(gid)) #+': '+message['message']['chat']['title']+'.')
    else:
        outdev.writeln('I\'ve been added back to group '+str(gid)) #+': '+message['message']['chat']['title']+'.')

def randomID():
    return hex(int.from_bytes(os.urandom(8),'big'))[2:]

def countWarn(db,gid,uid):
    if db[1].getItem(str(gid),'fade') == '0':
        return db[2].data.execute('select count(header) from warn where user=? and "group"=?',(str(uid),str(gid))).fetchone()[0]
    elif db[1].getItem(str(gid),'fade')[0] == '1':
        beforeTime = time.time() - int(db[1].getItem(str(gid),'fade').split('|')[1])
        counter = 0
        warnRec = db[2].data.execute('select time from warn where user=? and "group"=? and header != \'header\'',(str(uid),str(gid))).fetchall()
        # print(warnRec,beforeTime)
        for item in warnRec:
            counter += 1 if int(item[0]) > beforeTime else 0
        return counter

def getName(uid,gid,api,lookup={}):
    if uid in lookup:
        return '@'+lookup[uid]
    try:
        result = api.query('getChatMember',{'chat_id':int(gid),'user_id':int(uid)},retry=1)
    except APIError:
        return 'a former member of this group'
    return getNameRep(result['user'])

def getNameRep(userObj):
    if 'username' in userObj:
        return '@'+userObj['username']
    elif 'last_name' in userObj:
        return '@'+userObj['first_name']+' '+userObj['last_name']
    else:
        return '@'+userObj['first_name']

def getMsgText(msgObj):
    return msgObj['text'] if 'text' in msgObj else '<Multimedia Message>'

def getAdminList(adminList):
    result = {}
    for item in adminList:
        if item['status'] == 'creator' or (item['status'] == 'administrator' and 'can_restrict_members' in item):
            result[item['user']['id']] = getNameRep(item['user'])
    return result

def canPunish(api,gid):
    tmp = api.query('getChatMember',{'chat_id':gid,'user_id':api.info['id']})
    return tmp['status'] == 'creator' or ('can_restrict_members' in tmp and tmp['can_restrict_members'])

def processWarn(db,api,uo,gid,ts,reply):
    cannotPunish = not canPunish(api,gid)
    uid = str(uo['id'])
    uname = getNameRep(uo)
    api.logOut.writeln('Processing actual punishment...')
    warnNum = countWarn(db,gid,uid)
    if warnNum == 0:
        api.logOut.writeln("It does not qualify any warning.")
        return
    if warnNum > 5:
        warnNum = 5
    api.logOut.writeln(str(gid)+' '+str(db[1].hasItem(str(gid)))+' warning '+str(warnNum))
    punish = db[1].getItem(str(gid),'warning'+str(warnNum)).split('|')
    api.logOut.writeln(punish)
    # 0 - Nothing
    # 1 - Mute
    # 2 - Kick
    if punish[0] == '1':
        if len(punish) == 1 or punish[1] == '0':
            # Forever
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被永久禁言，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10),'can_send_messages':False})))
                api.sendMessage(gid,'該用戶已被永久禁言。',{'reply_to_message_id':reply})
                if db[1].getItem(str(gid),'notify') != 'None':
                    api.sendMessage(db[1].getItem(str(gid),'notify'),l10n.notifyPunish('silenced','forever',uname,uid))
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' ，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1]),'can_send_messages':False})))
                api.sendMessage(gid,'該用戶已被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 。',{'reply_to_message_id':reply})
                if db[1].getItem(str(gid),'notify') != 'None':
                    api.sendMessage(db[1].getItem(str(gid),'notify'),l10n.notifyPunish('silenced',l10n.epochToISO(int(ts)+int(punish[1])),uname,uid))
    if punish[0] == '2' or punish[0] == '3':
        if len(punish) == 1 or punish[1] == '0' or punish[0] == '3':
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被永久封禁，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10)})))
                api.sendMessage(gid,'該用戶已被永久封禁。',{'reply_to_message_id':reply})
                if db[1].getItem(str(gid),'notify') != 'None':
                    api.sendMessage(db[1].getItem(str(gid),'notify'),l10n.notifyPunish('kicked','forever',uname,uid))
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            # Can punish
            else:
                api.logOut.writeln(str(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1])})))
                api.sendMessage(gid,'該用戶已被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 。',{'reply_to_message_id':reply})
                if db[1].getItem(str(gid),'notify') != 'None':
                    api.sendMessage(db[1].getItem(str(gid),'notify'),l10n.notifyPunish('kicked',l10n.epochToISO(int(ts)+int(punish[1])),uname,uid))

def processRule(gid,db):
    result = '警告與懲罰規則：\n'
    data = [db[1].getItem(str(gid),'warning'+str(i)).split('|') for i in range(1,6)]
    while len(data) > 1 and data[-1] == data[-2]:
        data.pop() # Makes the list more compact
    for item in range(len(data)):
        if item == len(data)-1:
            result += str(item+1)+' 個或更多個警告：'
        else:
            result += str(item+1)+' 個警告：'
        if data[item][0] == '0':
            result += '口頭警告\n'
        elif data[item][0] == '1':
            if data[item][1] == '0':
                result += '永久禁言\n'
            else:
                result += '禁言 '+str(datetime.timedelta(seconds=int(data[item][1])))+'\n'
        elif data[item][0] == '2':
            result += '封禁 '+str(datetime.timedelta(seconds=int(data[item][1])))+'\n'
        elif data[item][0] == '3':
            result += '永久封禁\n'
    data = db[1].getItem(str(gid),'fade').split('|')
    if data[0] == '0':
        result += '警告期限：警告永不過期'
    elif data[0] == '1':
        result += '警告期限：'+str(datetime.timedelta(seconds=int(data[1])))
    elif data[0] == '2':
        result += '警告期限：每月 1 日解除 '+data[1]+' 個警告。'
    return result

def processCheck(msg,api,db):
    if msg['message']['chat']['type'] == 'private':
    # Check the warnings for the user itself across the globe
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented D:',{'reply_to_message_id':message['message']['message_id']})
    elif msg['message']['chat']['type'] == 'supergroup':
    # Check the warnings for the user itself within the group
        data = db[2].data
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented.',{'reply_to_message_id':message['message']['message_id']})

def processItem(message,db,api):
    #print(message)
    db[0].addItem(['lastid',message['update_id']])
    api.logOut.writeln(str(message['update_id'])+' being processed...')
    if 'message' not in message:
        return
    if 'text' in message['message'] and message['message']['text']:
        # Process bot command
        if message['message']['text'][0] == '/':
            stripText = message['message']['text']
            if '@'+api.info['username'] in stripText:
                stripText=stripText[:-len(api.info['username'])-1]
            if stripText == '/ping':
                api.sendMessage(message['message']['chat']['id'],'Hell o\'world! It took '+str(time.time()-message['message']['date'])+' seconds!',{'reply_to_message_id':message['message']['message_id']})
            if stripText == '/anyone':
                api.sendMessage(message['message']['chat']['id'],'沒有人，你悲劇了。',{'reply_to_message_id':message['message']['reply_to_message']['message_id'] if 'reply_to_message' in message['message'] else message['message']['message_id']})
            ## EASTER EGGS
            elif stripText == '/stupid_bluedeck':
                api.sendMessage(message['message']['chat']['id'],'藍桌，真的是笨桌！',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/wpwpw':
                api.sendMessage(message['message']['chat']['id'],'白磷白磷白',{'reply_to_message_id':message['message']['message_id']})
            ##
            elif stripText == '/groupid':
                api.sendMessage(message['message']['chat']['id'],'Group ID: '+str(message['message']['chat']['id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == "/userid":
                api.sendMessage(message['message']['chat']['id'],'User ID: '+str(message['message']['reply_to_message']['from']['id'] if 'reply_to_message' in message['message'] else message['message']['from']['id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/lastid':
                api.sendMessage(message['message']['chat']['id'],'Last Message ID: '+str(message['update_id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/uptime':
                import subprocess
                api.sendMessage(message['message']['chat']['id'],'Uptime: '+subprocess.check_output('uptime').decode().strip(),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == "/warn":
                api.sendMessage(message['message']['chat']['id'],'本機器人可以用於警告用戶，請使用 #warn 附帶理由以作出警告。',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warnrule':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    api.sendMessage(message['message']['chat']['id'],processRule(message['message']['chat']['id'],db),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warncheck':
                processCheck(message,api,db)
        # Process hashtag
        # Hashtag shall only be accepted in supergroup issued by admin
        elif message['message']['text'][0] == '#':
            if len(message['message']['text'])>4 and message['message']['text'][1:5].lower() == 'warn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = getAdminList(api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']}))
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #WARN 警告其他用戶。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆需要被警告的訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif db[2].data.execute('SELECT count(header) from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()[0]:
                        warnInfo = db[2].data.execute('SELECT time,admin,reason from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()
                        api.sendMessage(message['message']['chat']['id'],l10n.warnedFail(l10n.epochToISO(int(warnInfo[0])),getName(warnInfo[1],message['message']['chat']['id'],api,adminList),warnInfo[2]),{'reply_to_message_id':message['message']['message_id']})
                    else:
                        warnInfo = [int(time.time()),message['message']['chat']['id'],message['message']['reply_to_message']['from']['id'],message['message']['reply_to_message']['message_id'],message['message']['from']['id'],message['message']['text'][5:].strip()]
                        if not warnInfo[-1]:
                            api.sendMessage(message['message']['chat']['id'],'用法錯誤：請提供警告理由，使對方明白何處做錯。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] in adminList:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告管理員，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] == api.info['id'] or message['message']['reply_to_message']['from']['is_bot']:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告機器人，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            wid = [randomID()]
                            while db[2].hasItem(wid[0]):
                                wid = [randomID()]
                            db[2].addItem(wid+warnInfo)
                            rep = api.sendMessage(message['message']['chat']['id'],l10n.warnSuccess(str(countWarn(db,warnInfo[1],warnInfo[2])),db[1].getItem(str(message['message']['chat']['id']),'msg')),{'reply_to_message_id':message['message']['message_id']})
                            #  i,t,u,uid,a,c,m,r
                            if db[1].getItem(str(message['message']['chat']['id']),'notify') != 'None':
                                api.sendMessage(db[1].getItem(str(message['message']['chat']['id']),'notify'),l10n.notifyWarn(wid[0],l10n.epochToISO(warnInfo[0]),getNameRep(message['message']['reply_to_message']['from']),str(warnInfo[2]),getNameRep(message['message']['from']),str(countWarn(db,warnInfo[1],warnInfo[2])),message['message']['reply_to_message']['text'] if 'text' in message['message']['reply_to_message'] else None,warnInfo[-1]))
                            # api.logOut.writeln('Warned '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                            processWarn(db,api,message['message']['reply_to_message']['from'],warnInfo[1],message['message']['reply_to_message']['date'],rep)
            elif len(message['message']['text'])>7 and message['message']['text'][1:8].lower() == 'delwarn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = {i['user']['id']:getNameRep(i['user']) for i in api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']})}
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #DELWARN 解除對其他用戶的警告。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆被警告用戶發送的原始訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif db[2].data.execute('SELECT count(header) from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()[0] == 0:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：該條訊息並未被警告過，請回覆被警告用戶發送的原始訊息。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        warnInfo = db[2].data.execute('SELECT time,admin,reason,header from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()
                        db[2].remItem(warnInfo[-1])
                        # api.logOut.writeln('Removed warning for '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                        api.sendMessage(message['message']['chat']['id'],l10n.delWarnSuccess(l10n.epochToISO(int(warnInfo[0])),getName(warnInfo[1],message['message']['chat']['id'],api,adminList),warnInfo[2],str(countWarn(db,message['message']['chat']['id'],message['message']['reply_to_message']['from']['id']))),{'reply_to_message_id':message['message']['message_id']})
                        #  i,t,u,uid,a,c,m,r
                        if db[1].getItem(str(message['message']['chat']['id']),'notify') != 'None':
                            api.sendMessage(db[1].getItem(str(message['message']['chat']['id']),'notify'),l10n.notifyDelwarn(warnInfo[-1],l10n.epochToISO(int(time.time())),getNameRep(message['message']['reply_to_message']['from']),str(message['message']['reply_to_message']['from']['id']),getNameRep(message['message']['from']),str(countWarn(db,message['message']['chat']['id'],message['message']['reply_to_message']['from']['id'])),message['message']['reply_to_message']['text'] if 'text' in message['message']['reply_to_message'] else None,message['message']['text'][8:].strip()))
            elif len(message['message']['text'])>3 and message['message']['text'][1:4].lower() == 'g11':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                elif db[1].getItem(str(message['message']['chat']['id']),'notify') == 'None':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，該功能僅在已配置群組日誌的群可用。您可以直接使用濫權三連（刪除消息，封禁用戶，舉報用戶）處理 #G11。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = getAdminList(api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']}))
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #G11 快速踢出其他用戶。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆需要被處理的訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif message['message']['reply_to_message']['from']['id'] in adminList:
                        api.sendMessage(message['message']['chat']['id'],'竟敢試圖說管理員有 #G11 ，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                    elif message['message']['reply_to_message']['from']['id'] == api.info['id'] or message['message']['reply_to_message']['from']['is_bot']:
                        api.sendMessage(message['message']['chat']['id'],'竟敢試圖 #G11 機器人，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                    elif not canPunish(api,message['message']['chat']['id']):
                        api.sendMessage(message['message']['chat']['id'],'雖然很想處理掉這個 #G11 ，然而本機器人流下了沒有權利的淚水。您可以直接使用濫權三連（刪除消息，封禁用戶，舉報用戶）處理 #G11。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        ## Process G11
                        api.query('kickChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['reply_to_message']['from']['id']})
#                        api.sendMessage(db[1].getItem(str(message['message']['chat']['id'],'notify')),l10n.notifyG11(str(int(time.time())),getNameRep(message['message']['reply_to_message']['from']),str(message['message']['reply_to_message']['from']['id']),getNameRep(message['message']['from']),message['message']['reply_to_message']))
                        api.sendMessage(db[1].getItem(str(message['message']['chat']['id']),'notify'),getNameRep(message['message']['from'])+" has killed a #G11 from "+getNameRep(message['message']['reply_to_message']['from'])+"("+ str(message['message']['reply_to_message']['from']['id'])+") with content of\n"+getMsgText(message['message']['reply_to_message']))
                        print(str(int(time.time())),getNameRep(message['message']['reply_to_message']['from']),str(message['message']['reply_to_message']['from']['id']),getNameRep(message['message']['from']),message['message']['reply_to_message'])
                        try:
                            api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['reply_to_message']['message_id']})
                        except APIError:
                            api.sendMessage(message['message']['chat']['id'],'機器人似乎在試圖刪除該消息時遇到了一些困難。',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            api.sendMessage(message['message']['chat']['id'],'機器人成功處理掉了一個 #G11 ！',{'reply_to_message_id':message['message']['message_id']})
            elif len(message['message']['text'])>11 and message['message']['text'][1:12].lower() == 'setwarnrule':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    reqUser = api.query('getChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['from']['id']})
                    if (reqUser['status'] != 'creator') and (('can_promote_members' in reqUser) and reqUser['can_promote_members']):
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #SETWARNRULE 修改警告懲罰規則。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        newRule = message['message']['text'].split('\n')[1:]
                        if not newRule:
                            api.sendMessage(message['message']['chat']['id'],"規則說明：每行一條，使用下列格式聲明規則\n\n規則類型：\n0: 口頭警告\n1|x: 禁言 x 秒\n2|x: 封禁 x 秒\n3: 永封\n\n警告規則不超過 5 條",{"reply_to_message_id":message['message']['message_id']})
                        else:
                            dbRule = []
                            for i in range(len(newRule)):
                                tmp = newRule[i].split('|')
                                if (not tmp[0]) or (tmp[0] not in '0123') or ((tmp[0] in '03') and len(tmp) != 1) or ((tmp[0] in '12') and len(tmp) not in (1,2)):
                                    api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNRULE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                    dbRule = None
                                    break
                                elif tmp[0] in '12' and len(tmp) == 2:
                                    try:
                                        tmp[0] += '|'+str(int(tmp[1]))
                                    except ValueError:
                                        api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNRULE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                        dbRule = None
                                        break
                                dbRule.append(tmp[0])
                            if dbRule:
                                tmp = [str(message['message']['chat']['id'])]+dbRule
                                tmp += [dbRule[-1]] * (6-len(tmp))
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'fade')]
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'notify')]
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'msg')]
                                db[1].addItem(tmp)
                                api.sendMessage(message['message']['chat']['id'],"警告懲罰規則已修改成功。",{'reply_to_message_id':message['message']['message_id']})
            elif len(message['message']['text'])>11 and message['message']['text'][1:12].lower() == 'setwarnfade':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    reqUser = api.query('getChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['from']['id']})
                    if (reqUser['status'] != 'creator') and (('can_promote_members' in reqUser) and reqUser['can_promote_members']):
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #SETWARNFADE 修改警告懲罰規則。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        newRule = message['message']['text'].split(' ')[1:]
                        invalidRule = False
                        if not newRule:
                            api.sendMessage(message['message']['chat']['id'],"用法說明：\n#SETWARNFADE 規則\n\n規則類型：\n0: 警告永不過期\n1|x: 警告 x 秒後過期",{'reply_to_message_id':message['message']['message_id']})
                            invalidRule = True
                        else:
                            dbRule = newRule[0].split('|')
                            if (dbRule[0] == '1' and len(dbRule) != 2) or (dbRule[0] == '0' and len(dbRule) != 1):
                                api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNFADE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                invalidRule = True
                            else:
                                if dbRule[0] == '1':
                                    try:
                                        dbRule[0] += '|'+str(int(dbRule[1]))
                                    except ValueError:
                                        api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNFADE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                        invalidRule = True
                            if not invalidRule:
                                db[1].data.execute('UPDATE "group" SET "fade"=? WHERE header=?',(dbRule[0],str(message['message']['chat']['id'])))
                                db[1].db.commit()
                                api.sendMessage(message['message']['chat']['id'],"警告過期規則已修改成功。",{'reply_to_message_id':message['message']['message_id']})

    elif 'new_chat_members' in message['message']:
        for newMember in message['message']['new_chat_members']:
            if newMember['id'] == api.info["id"]:
                addGroup(message['message']['chat']['id'],db,api.logOut)
                groupBlacklist = db[0].getItem('blacklist','value').split('|')
                if str(message['message']['chat']['id']) in groupBlacklist:
                    try:
                        api.sendMessage(message['message']['chat']['id'],"This group has been blacklisted!")
                    except APIError:
                        api.logOut.writeln("Group blacklisted message failed to be sent")
                    api.query("leaveChat",{"chat_id":message['message']['chat']['id']})
    db[0].addItem(['lasttime',message['message']['date']])

def run(db,api):
    data = api.query('getUpdates')
    resPos = int(db[0].getItem('lastid','value'))
    for item in range(len(data)):
        if data[item]['update_id'] == resPos:
            data = data[item+1:]
            api.logOut.writeln('Skipping '+str(item+1)+' processed messages.')
            break
    for item in data:
        processItem(item,db,api)
    api.logOut.writeln('All pending messages processed.')
    while True:
        time.sleep(2) #Max frequency 30 messages/group
        data = api.query('getUpdates',{'offset':int(db[0].getItem('lastid','value'))+1,'timeout':20})
        for item in data:
            processItem(item,db,api)

def main(args):
    outdev = stdOut(args[2]) if len(args)==3 else stdOut()
    if len(args) not in (2,3):
        print('FATAL ERROR: Incorrect number of parameters given.')
        print(__doc__)
        sys.exit(1)
    try:
        api = tgapi(args[1],outdev)
    except APIError:
        print('FATAL ERROR: API Initialization Self-test Failed.')
        sys.exit(2)
    try:
        db = initiateDB(args[0],outdev)
    except APIError:
        print('FATAL ERROR: Corrupted database or wrong parameter given.')
        sys.exit(3)
    print('The configurations have been loaded successfully.')
    run(db,api)

if __name__ == '__main__':
    main(sys.argv[1:])
