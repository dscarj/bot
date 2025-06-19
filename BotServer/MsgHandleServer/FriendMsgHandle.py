from BotServer.BotFunction.InterfaceFunction import *
from BotServer.BotFunction.JudgeFuncion import *
from ApiServer.ApiMainServer import ApiMainServer
from DbServer.DbMainServer import DbMainServer
import xml.etree.ElementTree as ET
import Config.ConfigServer as Cs
from OutPut.outPut import op
from threading import Thread


class FriendMsgHandle:
    def __init__(self, wcf):
        """
        关键词拉群 yes
        好友消息转发给超管 yes
        好友Ai消息 yes
        自定义关键词回复 yes
        管理员公众号消息转发给推送群聊 yes
        查看白名单群聊 yes
        查看黑名单群聊 yes
        查看推送群聊 yes
        查看黑名单公众号 yes
        好友红包消息处理 yes
        好友转账接收 yes 微信版本过低无法使用
        :param wcf:
        """
        self.wcf = wcf
        self.Dms = DbMainServer()
        self.Ams = ApiMainServer()
        configData = Cs.returnConfigData()

        # 超级管理员列表
        self.Administrators = configData['SystemConfig']['Administrators']
        # 功能关键词配置
        self.sendMsgKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['SendMsgKeyWords']
        self.showWhiteRoomKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['ShowWhiteRoomKeyWords']
        self.showBlackRoomKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['ShowBlackRoomKeyWords']
        self.showPushRoomKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['ShowPushRoomKeyWords']
        self.showBlackGhKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['ShowBlackGhKeyWords']

        # 系统配置
        self.aiLock = configData['SystemConfig']['AiLock']
        self.acceptMoneyLock = configData['SystemConfig']['AcceptMoneyLock']
        self.acceptFriendLock = configData['SystemConfig']['AcceptFriendConfig']['AcceptFriendLock']
        self.msgForwardAdmin = configData['SystemConfig']['MsgForwardAdmin']
        self.acceptFriendMsg = configData['SystemConfig']['AcceptFriendConfig']['AcceptFriendMsg']

        # 自定义配置
        self.roomKeyWords = configData['JoinGroupConfig']['JoinGroupKeyWordsConfig']
        self.customKeyWords = configData['CustomConfig']

        # 给好友发消息关键词
        self.sendMsgKeyWords = configData['FunctionConfig']['AdminFunctionConfig']['SendMsgKeyWords']

    def mainHandle(self, msg):
        content = msg.content.strip()
        sender = msg.sender
        msgType = msg.type
        # print(msgType)

        if msgType == 1:
            # 关键词进群
            if judgeEqualListWord(content, self.roomKeyWords.keys()):
                # self.keyWordJoinRoom(sender, content)
                Thread(target=self.keyWordJoinRoom, args=(sender, content)).start()
            # 自定义关键词回复功能
            elif judgeEqualListWord(content, self.customKeyWords.keys()):
                # self.customKeyWordMsg(sender, content)
                Thread(target=self.customKeyWordMsg, args=(sender, content)).start()
            # 查看白名单群聊
            elif judgeEqualListWord(content, self.showWhiteRoomKeyWords) and sender in self.Administrators:
                # self.showWhiteRoom(sender, )
                Thread(target=self.showWhiteRoom, args=(sender,)).start()
            # 查看黑名单群聊
            elif judgeEqualListWord(content, self.showBlackRoomKeyWords) and sender in self.Administrators:
                # self.showBlackRoom(sender, )
                Thread(target=self.showBlackRoom, args=(sender,)).start()
            # 查看推送群聊
            elif judgeEqualListWord(content, self.showPushRoomKeyWords) and sender in self.Administrators:
                # self.showPushRoom(sender, )
                Thread(target=self.showPushRoom, args=(sender,)).start()
            # 查看黑名单公众号
            elif judgeEqualListWord(content, self.showBlackGhKeyWords) and sender in self.Administrators:
                # self.showBlackGh(sender, )
                Thread(target=self.showBlackGh, args=(sender,)).start()
                # 超级管理员发消息转发给好友
            elif judgeSplitAllEqualWord(content, self.sendMsgKeyWords):
                Thread(target=self.sendFriendMsg, args=(content,)).start()
            # Ai对话 Ai锁功能 对超管没用
            elif self.aiLock or sender in self.Administrators:
                Thread(target=self.getAiMsg, args=(content, sender)).start()
            # 好友消息转发给超级管理员 超级管理员不触发
            if sender not in self.Administrators and self.msgForwardAdmin:
                Thread(target=self.forwardMsgToAdministrators, args=(sender, content)).start()
        elif msgType == 34 and self.aiLock or (sender in self.Administrators and msgType == 34):
            # 语音Ai回复
            Thread(target=self.getAudioAiMsg, args=(msg.id, sender)).start()
        # 转发公众号消息到推送群聊 超管有效
        if msg.type == 49:
            # 公众号卡片转发给推送群聊
            if msg.sender in self.Administrators and 'gh_' in msg.content:
                Thread(target=self.forwardGhMsg, args=(msg.id,)).start()
            # 图文Ai对话
            elif 'cdnmidimgurl' in content:
                Thread(target=self.getAiPicDia, args=(msg, )).start()
            # 暂时没用 等Hook作者更新 老版本微信有用
            elif '转账' in msg.content and self.acceptMoneyLock:
                Thread(target=self.acceptMoney, args=(msg,)).start()
            # 引用Ai对话
            else:
                Thread(target=self.getQuoteAi, args=(content, sender)).start()
        # 红包消息处理 转发红包消息给主人
        if msgType == 10000 and '请在手机上查看' in msg.content:
            Thread(target=self.forwardRedPacketMsg, args=(sender,)).start()
        # 好友自动同意处理 暂时没用 老版本微信有用
        if msgType == 37 and self.acceptFriendLock:
            Thread(target=self.acceptFriend, args=(msg,)).start()

    def getQuoteAi(self, content, sender):
        """
        引用Ai回复
        :param content:
        :return:
        """
        try:
            srvType, srvContent, srvTitle = getQuoteMsgData(content)
            if srvType == 1:
                content = f'用户描述的内容: {srvContent}\n以上是用户描述的内容, 请根据用户描述的内容和用户提问的内容给我回复！\n用户提问的内容: {srvTitle}'
                self.getAiMsg(content=content, sender=sender)
        except Exception as e:
            pass

    def getAiPicDia(self, msg):
        """
        图文对话
        :param msg:
        :return:
        """
        srvType, srvId, srvContent = getQuoteImageData(msg.content)
        if srvType == 3:
            srvImagePath = downloadQuoteImage(self.wcf, srvId, msg.extra)
            if srvImagePath:
                aiMsg = self.Ams.getAiPicDia(srvContent, srvImagePath, msg.sender)
                if not aiMsg:
                    self.wcf.send_text(
                        f'Ai图文对话接口出现错误, 请联系超管查看控制台输出日志',
                        receiver=msg.sender)
                    return
                if 'FileCache' in aiMsg:
                    self.wcf.send_image(aiMsg, receiver=msg.sender)
                    return
                if aiMsg:
                    self.wcf.send_text(aiMsg, receiver=msg.sender)


    def acceptFriend(self, msg):
        """
        同意好友申请处理
        :return:
        """
        try:
            root_xml = ET.fromstring(msg.content.strip())
            wxId = root_xml.attrib["fromusername"]
            op(f'[*]: 接收到新的好友申请, 微信id为: {wxId}')
            v3 = root_xml.attrib["encryptusername"]
            v4 = root_xml.attrib["ticket"]
            scene = int(root_xml.attrib["scene"])
            ret = self.wcf.accept_new_friend(v3=v3, v4=v4, scene=scene)
            acceptSendMsg = self.acceptFriendMsg.replace('\\n', '\n')
            self.wcf.send_text(acceptSendMsg, receiver=wxId)
            if ret:
                op(f'[+]: 好友 {getIdName(self.wcf, wxId)} 已自动通过 !')
            else:
                op(f'[-]: 好友通过失败！！！')
        except Exception as e:
            op(f'[-]: 自动通过好友出现错误, 错误信息: {e}')

    def acceptMoney(self, msg):
        """
        处理转账消息, 只处理好友转账
        :param msg:
        :return:
        """
        root_xml = ET.fromstring(msg.content.strip())
        title_element = root_xml.find(".//title")
        title = title_element.text if title_element is not None else None
        if '微信转账' == title and msg.sender != self.wcf.self_wxid:
            transCationId = root_xml.find('.//transcationid').text
            transFerid = root_xml.find('.//transferid').text
            if not self.wcf.receive_transfer(wxid=msg.sender, transactionid=transCationId,
                                             transferid=transFerid):
                op(f'[-]: 接收好友转账失败, 可能是版本不支持')

    def forwardRedPacketMsg(self, sender):
        """
        转发红包消息给主人
        :return:
        """
        for administrator in self.Administrators:
            self.wcf.send_text(f'[爱心]接收到好友: {getIdName(self.wcf, sender)} 的红包, 请在手机上接收',
                               receiver=administrator)
        self.wcf.send_text(f'[爱心]已接收到您的红包, 感谢支持', receiver=sender)

    def showBlackGh(self, sender):
        """
        查看黑名单公众号
        :param sender:
        :return:
        """
        blackGhData = self.Dms.showBlackGh()
        sendMsg = '===== 推送群聊列表 =====\n'
        for roomId, roomName in blackGhData.items():
            sendMsg += f'公众号ID: {roomId}\n公众号昵称: {roomName}\n---------------\n'
        if not blackGhData:
            sendMsg = '暂无公众号添加至黑名单'
        self.wcf.send_text(sendMsg, receiver=sender)

    def showPushRoom(self, sender):
        """
        查看推送群聊
        :param sender:
        :return:
        """
        pushRoomData = self.Dms.showPushRoom()
        sendMsg = '===== 推送群聊列表 =====\n'
        for roomId, roomName in pushRoomData.items():
            sendMsg += f'群聊ID: {roomId}\n群聊昵称: {roomName}\n---------------\n'
        if not pushRoomData:
            sendMsg = '暂无群聊开启推送服务'
        self.wcf.send_text(sendMsg, receiver=sender)

    def showBlackRoom(self, sender):
        """
        查看黑名单群聊 超管有效
        :return:
        """
        blackRoomData = self.Dms.showBlackRoom()
        sendMsg = '===== 黑名单群聊列表 =====\n'
        for roomId, roomName in blackRoomData.items():
            sendMsg += f'群聊ID: {roomId}\n群聊昵称: {roomName}\n---------------\n'
        if not blackRoomData:
            sendMsg = '暂无群聊添加至黑名单'
        self.wcf.send_text(sendMsg, receiver=sender)

    def showWhiteRoom(self, sender):
        """
        查看白名单群聊 超管有效
        :return:
        """
        whiteRoomData = self.Dms.showWhiteRoom()
        sendMsg = '===== 白名单群聊列表 =====\n'
        for roomId, roomName in whiteRoomData.items():
            sendMsg += f'群聊ID: {roomId}\n群聊昵称: {roomName}\n---------------\n'
        if not whiteRoomData:
            sendMsg = '暂无群聊添加至白名单'
        self.wcf.send_text(sendMsg, receiver=sender)

    def forwardGhMsg(self, msgId):
        """
        转发公众号消息到推送群来哦 超管有效
        :param msgId:
        :return:
        """
        pushRoomDicts = self.Dms.showPushRoom()
        for pushRoomId in pushRoomDicts.keys():
            self.wcf.forward_msg(msgId, receiver=pushRoomId)

    def customKeyWordMsg(self, sender, content):
        """
        自定义关键词消息回复
        :param sender:
        :param content:
        :return:
        """
        for keyWord in self.customKeyWords.keys():
            if judgeEqualWord(content, keyWord):
                replyMsgLists = self.customKeyWords.get(keyWord)
                for replyMsg in replyMsgLists:
                    self.wcf.send_text(replyMsg, receiver=sender)

    def keyWordJoinRoom(self, sender, content):
        """
        关键词进群
        :param sender:
        :param content:
        :return:
        """
        for keyWord in self.roomKeyWords.keys():
            if judgeEqualWord(content, keyWord):
                roomLists = self.roomKeyWords.get(keyWord)
                for roomId in roomLists:
                    roomMember = self.wcf.get_chatroom_members(roomId)
                    if len(roomMember) == 500:
                        continue
                    if sender in roomMember.keys():
                        self.wcf.send_text(f'你小子已经进群了, 还想干吗[旺柴]', receiver=sender)
                        break
                    if self.wcf.invite_chatroom_members(roomId, sender):
                        op(f'[+]: 已将 {sender} 拉入群聊【{roomId}】')
                        break
                    else:
                        op(f'[-]: {sender} 拉入群聊【{roomId}】失败 !!!')

    def sendFriendMsg(self, content):
        """
        给好友发消息 只对超管生效
        :param content:
        :return:
        """
        wxId = content.split(' ')[1]
        sendMsg = f'==== [爱心]来自超管的消息[爱心] ====\n\n{content.split(" ")[-1]}\n\n====== [爱心]NGCBot[爱心] ======'
        self.wcf.send_text(sendMsg, receiver=wxId)

    def getAudioAiMsg(self, msgId, sender):
        """
        好友语音AI回复
        :param msgId
        :param sender:
        :return:
        """
        audioPath = self.wcf.get_audio_msg(msgId, Fcs.returnAudioFolder())
        if not audioPath:
            op(f'[-]: 语音Ai回复出现错误, 获取不到语音文件路径！')
            return
        audioMsg = self.Ams.getAudioMsg(audioPath)
        if not audioMsg:
            op(f'[-]: 语音Ai回复出现错误, 语音文本返回为空！')
            return
        self.getAiMsg(content=audioMsg, sender=sender)

    def getAiMsg(self, content, sender):
        """
        好友Ai对话
        :param content:
        :param sender:
        :return:
        """
        aiMsg = self.Ams.getAi(content, sender)
        if not aiMsg:
            self.wcf.send_text(f'Ai对话接口出现错误, 请稍后再试 ~~~', receiver=sender)
            return
        if 'FileCache' in aiMsg:
            self.wcf.send_image(aiMsg, receiver=sender)
            return
        if aiMsg:
            self.wcf.send_text(aiMsg, receiver=sender)


    def forwardMsgToAdministrators(self, wxId, content):
        """
        好友消息转发给超级管理员
        :param wxId:
        :param content:
        :return:
        """
        forwardMsg = f"= [爱心]收到来自好友的消息[爱心] =\n好友ID: {wxId}\n好友昵称: {getIdName(self.wcf, wxId)}\n好友消息: {content}\n====== [爱心]NGCBot[爱心] ======"
        for administrator in self.Administrators:
            self.wcf.send_text(forwardMsg, receiver=administrator)


if __name__ == '__main__':
    Fmh = FriendMsgHandle(1)
    # Fmh.showWhiteRoom()
