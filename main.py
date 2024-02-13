import argparse
import traceback
import asyncio
import google.generativeai as genai
import re
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.types import  Message
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = []

error_info="⚠️⚠️⚠️\مش فاهم !\ممكن تكتب رسالتك بشكل مختلف او تتواصل مع الادمن !"
before_generate_info="🤖Generating🤖"
download_pic_notify="🤖Loading picture🤖"

def find_all_index(str, pattern):
    index_list = [0]
    for match in re.finditer(pattern, str, re.MULTILINE):
        if match.group(1) != None:
            start = match.start(1)
            end = match.end(1)
            index_list += [start, end]
    index_list.append(len(str))
    return index_list


def replace_all(text, pattern, function):
    poslist = [0]
    strlist = []
    originstr = []
    poslist = find_all_index(text, pattern)
    for i in range(1, len(poslist[:-1]), 2):
        start, end = poslist[i : i + 2]
        strlist.append(function(text[start:end]))
    for i in range(0, len(poslist), 2):
        j, k = poslist[i : i + 2]
        originstr.append(text[j:k])
    if len(strlist) < len(originstr):
        strlist.append("")
    else:
        originstr.append("")
    new_list = [item for pair in zip(originstr, strlist) for item in pair]
    return "".join(new_list)

def escapeshape(text):
    return "▎*" + text.split()[1] + "*"

def escapeminus(text):
    return "\\" + text

def escapebackquote(text):
    return r"\`\`"

def escapeplus(text):
    return "\\" + text

def escape(text, flag=0):
    # In all other places characters
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    # must be escaped with the preceding character '\'.
    text = re.sub(r"\\\[", "@->@", text)
    text = re.sub(r"\\\]", "@<-@", text)
    text = re.sub(r"\\\(", "@-->@", text)
    text = re.sub(r"\\\)", "@<--@", text)
    if flag:
        text = re.sub(r"\\\\", "@@@", text)
    text = re.sub(r"\\", r"\\\\", text)
    if flag:
        text = re.sub(r"\@{3}", r"\\\\", text)
    text = re.sub(r"_", "\_", text)
    text = re.sub(r"\*{2}(.*?)\*{2}", "@@@\\1@@@", text)
    text = re.sub(r"\n{1,2}\*\s", "\n\n• ", text)
    text = re.sub(r"\*", "\*", text)
    text = re.sub(r"\@{3}(.*?)\@{3}", "*\\1*", text)
    text = re.sub(r"\!?\[(.*?)\]\((.*?)\)", "@@@\\1@@@^^^\\2^^^", text)
    text = re.sub(r"\[", "\[", text)
    text = re.sub(r"\]", "\]", text)
    text = re.sub(r"\(", "\(", text)
    text = re.sub(r"\)", "\)", text)
    text = re.sub(r"\@\-\>\@", "\[", text)
    text = re.sub(r"\@\<\-\@", "\]", text)
    text = re.sub(r"\@\-\-\>\@", "\(", text)
    text = re.sub(r"\@\<\-\-\@", "\)", text)
    text = re.sub(r"\@{3}(.*?)\@{3}\^{3}(.*?)\^{3}", "[\\1](\\2)", text)
    text = re.sub(r"~", "\~", text)
    text = re.sub(r">", "\>", text)
    text = replace_all(text, r"(^#+\s.+?$)|```[\D\d\s]+?```", escapeshape)
    text = re.sub(r"#", "\#", text)
    text = replace_all(
        text, r"(\+)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escapeplus
    )
    text = re.sub(r"\n{1,2}(\s*)-\s", "\n\n\\1• ", text)
    text = re.sub(r"\n{1,2}(\s*\d{1,2}\.\s)", "\n\n\\1", text)
    text = replace_all(
        text, r"(-)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escapeminus
    )
    text = re.sub(r"```([\D\d\s]+?)```", "@@@\\1@@@", text)
    text = replace_all(text, r"(``)", escapebackquote)
    text = re.sub(r"\@{3}([\D\d\s]+?)\@{3}", "```\\1```", text)
    text = re.sub(r"=", "\=", text)
    text = re.sub(r"\|", "\|", text)
    text = re.sub(r"{", "\{", text)
    text = re.sub(r"}", "\}", text)
    text = re.sub(r"\.", "\.", text)
    text = re.sub(r"!", "\!", text)
    return text

async def make_new_gemini_convo():
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    convo = model.start_chat()
    return convo

async def main():
    # Init args
    parser = argparse.ArgumentParser()
    parser.add_argument("tg_token", help="telegram token")
    parser.add_argument("GOOGLE_GEMINI_KEY", help="Google Gemini API key")
    options = parser.parse_args()
    print("Arg parse done.")
    gemini_player_dict = {}

    genai.configure(api_key=options.GOOGLE_GEMINI_KEY)

    # Init bot
    bot = AsyncTeleBot(options.tg_token)
    await bot.delete_my_commands(scope=None, language_code=None)
    await bot.set_my_commands(
        commands=[
            telebot.types.BotCommand("start", "Start"),
            telebot.types.BotCommand("clear", "Clear history")
        ],
    )
    print("Bot init done.")

    # Init commands
    @bot.message_handler(commands=["start"])
    async def gemini_handler(message: Message):
        try:
            user_name = message.from_user.first_name

            await bot.reply_to( message , escape(f"إزيك يا {user_name} أتمني انك تكون بخير انا بوت خاص ب GDSC AOU لو عايز حاجه ممكن تتكلم معايا انا مدرب علي داتا كبيره جدا في البرمجة واساله عامة \n لو عايز حاجه ممكن تنادي عليا قولي جوجل او G"), parse_mode="MarkdownV2")
        except IndexError:
            await bot.reply_to(message, error_info)

    @bot.message_handler(commands=["gemini"])
    async def gemini_handler(message: Message):

        if message.chat.type == "private":
            await bot.reply_to( message , "This command is only for chat groups !")
            return
        try:
            m = message.text.strip().split(maxsplit=1)[1].strip()
        except IndexError:
            await bot.reply_to( message , escape("Please add what you want to say after /gemini. \nFor example: `/gemini Who is john lennon?`"), parse_mode="MarkdownV2")
            return
        player = None
        if str(message.from_user.id) not in gemini_player_dict:
            player = await make_new_gemini_convo()
            gemini_player_dict[str(message.from_user.id)] = player
        else:
            player = gemini_player_dict[str(message.from_user.id)]
        if len(player.history) > 10:
            player.history = player.history[2:]
        try:
            sent_message = await bot.reply_to(message, before_generate_info)
            player.send_message(m)
            try:
                await bot.edit_message_text(escape(player.last.text), chat_id=sent_message.chat.id, message_id=sent_message.message_id, parse_mode="MarkdownV2")
            except:
                await bot.edit_message_text(escape(player.last.text), chat_id=sent_message.chat.id, message_id=sent_message.message_id)

        except Exception:
            traceback.print_exc()
            await bot.edit_message_text(error_info, chat_id=sent_message.chat.id, message_id=sent_message.message_id)

    @bot.message_handler(commands=["clear"])
    async def gemini_handler(message: Message):
        # Check if the player is already in gemini_player_dict.
        if str(message.from_user.id) in gemini_player_dict:
            del gemini_player_dict[str(message.from_user.id)]
            await bot.reply_to(message, "Your history has been cleared0")
        else:
            await bot.reply_to(message, "You have no history now")
    async def save_to_file(user_id, bot_answer, user_response):
        with open(f"user_feedback_{user_id}.txt", "a", encoding="utf-8") as file:
            file.write(f"Bot Answer: {bot_answer}\nUser Response: {user_response}\n\n")

    @bot.message_handler(func=lambda message: message.chat.type == "private", content_types=['text'])
    async def gemini_private_handler(message: Message):
        m = message.text.strip()
        player = None 
        # Check if the player is already in gemini_player_dict.
        if str(message.from_user.id) not in gemini_player_dict:
            player = await make_new_gemini_convo()
            gemini_player_dict[str(message.from_user.id)] = player
        else:
            player = gemini_player_dict[str(message.from_user.id)]
        # Control the length of the history record.
        user_name = message.from_user.first_name
            
        if len(player.history) > 10:
            player.history = player.history[2:]
        if "how are you" in m.lower():
            await bot.reply_to(message, "I'm good, thank you! How can I assist you?")
            return
        if  "google" in m.lower() or "جوجل" in m.lower():
            responses = [
                f"ايوة يا {user_name} إزاي ممكن اساعدك؟",
                f"أنا هنا للإجابة على أسئلتك، {user_name}.",
                f"جاهز لمساعدتك في البحث، {user_name}.",
                # يمكنك إضافة المزيد من الردود هنا
            ]
            response = random.choice(responses)
            await bot.reply_to(message, response)
            return
        elif "who are you" in m.lower():
            await bot.reply_to(message, "GDSC AOU EG Bot")
            return
        elif "انت مين" in m.lower():
            await bot.reply_to(message, "انا بوت اتعملت من GDSC AOU EG")
            return
        elif "اسمك" in m.lower():
            await bot.reply_to(message, "انا مليش اسم بس ممكن تقولي جوجل")
            return
    # التحقق مما إذا كانت رسالة المستخدم تحتوي على "ادخل"
        if "ادخل" in m:
            response = "عشان تدخل التيم لازم تقدم عن طريق الفورم اللى بينزل على صفحة التيم. لتفاصيل أكثر، اتفضل على اللينك: [رابط الفورم](https://example.com/form)"
            sent_message = await bot.reply_to(message, response, parse_mode="Markdown")
             

            return
    

        
        elif "gemini" in m.lower():
            await bot.reply_to(message, "Gemini موديل اتبرمج عن طريق جوجل")
            return
        if "محمود" in m.lower():
            linkedin_link = "https://linkedin.com/in/negrox1/"
            response = f"محمود النجار مبرمج باك اند خبرة أكثر من 4 سنوات وهو كمان ليد نادي مطوري جوجل في الجامعة العربية فرع مصر. يمكنك الاتصال به عبر [LinkedIn]({linkedin_link})"
            await bot.reply_to(message, response)
            return
        elif "تراكات" in m.lower():
            await bot.reply_to(message, "التراكات الموجودة كتيرة في مجالات البرمجة زي الويب و الذكاء الاصطناعي وغيره كدا مش بس تراكات التيك")
            return    
        elif "شامله" in m.lower():
            await bot.reply_to(message, "الكورسات تشمل مواضيع واسعة وشاملة لتمكين الطلاب من اكتساب مهارات شاملة في المجالات المختلفة")
            return
        elif "اوفلاين" in m.lower():
            await bot.reply_to(message, "بتختلف بيكون في كورسات اونلاين وكورسات اوفلاين")
            return
        elif "الشهاده" in m.lower() or "الشهادة" in m.lower() or "شهادة" in m.lower()  or "شهاده" in m.lower():
            await bot.reply_to(message, "ايوة بيكون في شهادة في نهاية الكورس وتقدر تحطها في ال cv")
            return
        elif "بكام" in m.lower():
            await bot.reply_to(message, "كل الكورسات الى بنقدمها فري تماما")
            return
        elif "cs" in m.lower():
            await bot.reply_to(message, "لا مش شرط تكون في كلية cs")
            return
        elif "خلفية" in m.lower() or "خلفيه" in m.lower():
            await bot.reply_to(message, "غالبا الكورسات الى بنقدمها بنبدأ معاك من الصفر")
            return
 
        try:
            sent_message = await bot.reply_to(message, before_generate_info)
            player.send_message(m)
            try:
            
                await bot.edit_message_text(escape(player.last.text), chat_id=sent_message.chat.id, message_id=sent_message.message_id, parse_mode="MarkdownV2")
            except:
                await bot.edit_message_text(escape(player.last.text), chat_id=sent_message.chat.id, message_id=sent_message.message_id)

        except Exception:
            traceback.print_exc()
            await bot.reply_to(message, error_info)
#########################################################
    async def save_user_input(user_id, input_text):
        try:
            with open("user_inputs.txt", "a") as file:
                file.write(f"User ID: {user_id}, Input: {input_text}\n")
            print(f"Saved user input to file: {input_text}")
        except Exception as e:
            print(f"Error saving user input to file: {e}")

    @bot.message_handler(func=lambda message: True, content_types=['text'])
    async def save_all_user_inputs(message):
        try:
            user_id = message.from_user.id
            input_text = message.text
            await save_user_input(user_id, input_text)
        except Exception as e:
            print(f"Error saving user input: {e}")
#########################################################
    @bot.message_handler(content_types=["photo"])
    async def gemini_photo_handler(message: Message) -> None:
        if message.chat.type != "private":
            s = message.caption
            if not s or not (s.startswith("/gemini")):
                return
            try:
                prompt = s.strip().split(maxsplit=1)[1].strip() if len(s.strip().split(maxsplit=1)) > 1 else ""
                file_path = await bot.get_file(message.photo[-1].file_id)
                sent_message = await bot.reply_to(message, download_pic_notify)
                downloaded_file = await bot.download_file(file_path.file_path)
            except Exception:
                traceback.print_exc()
                await bot.reply_to(message, error_info)
            model = genai.GenerativeModel("gemini-pro-vision")
            contents = {
                "parts": [{"mime_type": "image/jpeg", "data": downloaded_file}, {"text": prompt}]
            }
            try:
                await bot.edit_message_text(before_generate_info, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
                response = model.generate_content(contents=contents)
                await bot.edit_message_text(response.text, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
            except Exception:
                traceback.print_exc()
                await bot.edit_message_text(error_info, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
        else:
            s = message.caption if message.caption else ""
            try:
                prompt = s.strip()
                file_path = await bot.get_file(message.photo[-1].file_id)
                sent_message = await bot.reply_to(message, download_pic_notify)
                downloaded_file = await bot.download_file(file_path.file_path)
            except Exception:
                traceback.print_exc()
                await bot.reply_to(message, error_info)
            model = genai.GenerativeModel("gemini-pro-vision")
            contents = {
                "parts": [{"mime_type": "image/jpeg", "data": downloaded_file}, {"text": prompt}]
            }
            try:
                await bot.edit_message_text(before_generate_info, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
                response = model.generate_content(contents=contents)
                await bot.edit_message_text(response.text, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
            except Exception:
                traceback.print_exc()
                await bot.edit_message_text(error_info, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
    # Start bot
    print("Starting Gemini_Telegram_Bot.")
    await bot.polling(none_stop=True)

if __name__ == '__main__':
    asyncio.run(main())
