from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from . import message_text as mt
from . import keyboard_markups as km
import database
from spreadsheet import download_from_db, upload_to_db
from templates import generate_form
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

# Состояния, в которых может находится диалог
CATEGORY, GROUP_NAME, GENDER, SURNAME, NAME,\
MIDDLE_NAME, PHONE_NUMBER, INN, CHECK = range(9)

author_filter = Filters.user(377064896)
admins_filter = Filters.user(database.get_admins())


def start(update, context):
    """Отвечает на команду /start"""
    logger.info(f"User with chat_id {update.effective_user.id} sent /start")

    update.message.reply_text(mt.start)


def help(update, context):
    """Отвечает на команду /help"""
    # TODO: написать mt.help
    update.message.reply_text(...)


def make(update, context):
    """Отвечает на команду /make, предлагает выбрать категорию из списка"""
    logger.info(f"User with chat_id {update.effective_user.id} sent /make")

    update.message.reply_text(mt.category, reply_markup=km.categories_markup)
    context.user_data["state"] = CATEGORY
    return CATEGORY


def category(update, context):
    """
    Добавляет категорию в контекст пользователя и предлагает ввести группу.
    Информация, записанная в контексте юзера будет болтаться в рантайме, а
    когда студент подтвердит правильность введенных данных, добавится в бд
    """
    logger.info(f"User with chat_id {update.effective_user.id} selected category [{update.message.text}].")

    context.user_data[CATEGORY] = update.message.text

    update.message.reply_text(mt.group_name)
    context.user_data["state"] = GROUP_NAME
    return GROUP_NAME


def group_name(update, context):
    """Добавляет группу в контекст пользователя и предлагает ввести пол"""
    logger.info(f"User with chat_id {update.effective_user.id} sent group name [{update.message.text}]")

    context.user_data[GROUP_NAME] = update.message.text

    update.message.reply_text(mt.gender, reply_markup=km.genders_markup)
    context.user_data["state"] = GENDER
    return GENDER


def gender(update, context):
    """Добавляет пол в контекст пользователя и предлагает ввести фамилию"""
    logger.info(f"User with chat_id {update.effective_user.id} selected gender [{update.message.text}]")

    context.user_data[GENDER] = update.message.text

    update.message.reply_text(mt.surname)
    context.user_data["state"] = SURNAME
    return SURNAME


def surname(update, context):
    """Добавляет фамилию в контекст пользователя и предлагает ввести имя"""
    logger.info(f"User with chat_id {update.effective_user.id} sent surname [{update.message.text}]")

    context.user_data[SURNAME] = update.message.text

    update.message.reply_text(mt.name)
    context.user_data["state"] = NAME
    return NAME


def name(update, context):
    """Добавляет имя в контекст пользователя и предлагает ввести отчество"""
    logger.info(f"User with chat_id {update.effective_user.id} sent name [{update.message.text}]")

    context.user_data[NAME] = update.message.text

    update.message.reply_text(mt.middle_name)
    context.user_data["state"] = MIDDLE_NAME
    return MIDDLE_NAME


def middle_name(update, context):
    """Добавляет отчество в контекст пользователя и предлагает ввести номер телефона"""
    logger.info(f"User with chat_id {update.effective_user.id} sent middle name [{update.message.text}]")

    context.user_data[MIDDLE_NAME] = update.message.text

    update.message.reply_text(mt.phone_number)
    context.user_data["state"] = PHONE_NUMBER
    return PHONE_NUMBER


def phone_number(update, context):
    """Добавляет номер телефона в контекст пользователя и предлагает ввести ИНН"""
    logger.info(f"User with chat_id {update.effective_user.id} sent phone number [{update.message.text}]")

    context.user_data[PHONE_NUMBER] = update.message.text

    update.message.reply_text(mt.inn)
    context.user_data["state"] = INN
    return INN


def inn(update, context):
    """
    Добавляет ИНН в контекст пользователя и предлагает подтвердить
    правильность введенных данных
    """
    logger.info(f"User with chat_id {update.effective_user.id} sent INN [{update.message.text}]")

    context.user_data[INN] = update.message.text

    update.message.reply_text(
        mt.check + "{}\n{}\n{}\n{} {} {}\n{}\n{}".format(
            *[context.user_data[k] for k in range(8)]
        ), reply_markup=km.check_markup
    )
    context.user_data["state"] = CHECK
    return CHECK


def check(update, context):
    """
    Возвращает состояние CATEGORY, отправляя студента в начало диалога, или
    записывает данные из контекста пользователя в бд и отправляет в чат файл заявки
    """
    logger.info(f"User with chat_id {update.effective_user.id} selected [{update.message.text}]")

    if update.message.text == "Заполнить заявку заново":
        update.message.reply_text(mt.category, reply_markup=km.categories_markup)
        context.user_data["state"] = CATEGORY
        return CATEGORY

    data = [context.user_data[k] for k in range(8)]
    database.insert_application(data)

    form_bytes = generate_form(*data)
    update.message.reply_document(
        document=form_bytes,
        filename="application.docx",
        caption="Заявка принята!"
    )
    # Закрываем буфер
    form_bytes.close()
    return ConversationHandler.END


def wrong(update, context):
    """Хендлер обрабатывает любой неверный ввод и возвращает последнее состояние диалога"""
    logger.info(f"User with chat_id {update.effective_user.id} "
                f"sent wrong input [{update.message.text}] on state [{context.user_data['state']}]")

    update.message.reply_text(mt.wrong)
    return context.user_data["state"]


def download(update, context):
    """Отправляет xlsx файл, который содержит все заявки студентов"""
    logger.info(f"User with chat_id {update.effective_user.id} downloaded applications.xlsx")

    spreadsheet_bytes = download_from_db()
    # TODO: caption с инструкцией
    update.message.reply_document(
        document=spreadsheet_bytes,
        filename="applications.xlsx"
    )


def upload(update, context):
    """Обрабатывает загрузку xlsx файлов"""
    logger.info(f"User with chat_id {update.effective_user.id} uploaded applications spreadsheet")

    spreadsheet_bytes = BytesIO()
    update.message.document.get_file().download(
        out=spreadsheet_bytes
    )
    upload_to_db(spreadsheet_bytes)
    update.message.reply_text("База данных успешно обновлена!")


def guide(update, context):
    """Инструкция для админов"""

    logger.info(f"User with chat_id {update.effective_user.id} sent /guide")

    update.message.reply_text(mt.guide, ParseMode.HTML)


def faq(update, context):
    """Показывает список FAQ"""
    logger.info(f"User with chat_id {update.effective_user.id} sent /faq")

    update.message.reply_text(mt.faq, ParseMode.HTML)


def admins(update, context):
    """Возвращает список админов"""
    update.message.reply_text(
        "\n".join(map(str, admins_filter.user_ids))
    )


def add_admin(update, context):
    """Добавить пользователя в admins_filter и бд"""
    try:
        chat_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("Invalid chat_id! int expected")
    except IndexError:
        update.message.reply_text("Enter chat_id as command argument!")
    else:
        admins_filter.add_user_ids(chat_id)
        if database.insert_admin(chat_id):
            update.message.reply_text(f"User with chat_id {chat_id} has added to admins")
            logger.info(f"User with chat_id {chat_id} added to admins")
        else:
            update.message.reply_text(f"User with chat_id {chat_id} is already an admin!")


def remove_admin(update, context):
    """Удалить пользователя из admins_filter и бд"""
    try:
        chat_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("Invalid chat_id! int expected")
    except IndexError:
        update.message.reply_text("Enter chat_id as command argument!")
    else:
        admins_filter.remove_user_ids(chat_id)
        if database.delete_admin(chat_id):
            update.message.reply_text(f"User with chat_id {chat_id} has removed from admins")
            logger.info(f"User with chat_id {chat_id} removed from admins")
        else:
            update.message.reply_text(f"User with chat_id {chat_id} is not an admin!")


# Создаем хендлеры
start_handler = CommandHandler("start", start)
make_handler = CommandHandler("make", make)

admins_handler = CommandHandler(
    command="admins",
    callback=admins,
    filters=author_filter
)

add_admin_handler = CommandHandler(
    command="add_admin",
    callback=add_admin,
    filters=author_filter
)

remove_admin_handler = CommandHandler(
    command="remove_admin",
    callback=remove_admin,
    filters=author_filter
)

download_handler = CommandHandler(
    command="download",
    callback=download,
    filters=admins_filter
)

upload_handler = MessageHandler(
    callback=upload,
    filters=Filters.document.mime_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    & admins_filter
)

conv_handler = ConversationHandler(
    entry_points=[make_handler],
    states={
        CATEGORY:     [MessageHandler(Filters.text(database.get_categories_list()), category)],
        GROUP_NAME:   [MessageHandler(Filters.regex(r"^[А-ЯЁ]{3}-[1-5]{2}[1-9]$"), group_name)],
        GENDER:       [MessageHandler(Filters.text(["Мужской", "Женский"]), gender)],
        SURNAME:      [MessageHandler(Filters.regex(r"^[а-яёА-ЯЁ-]{1,20}$"), surname)],
        NAME:         [MessageHandler(Filters.regex(r"^[а-яёА-ЯЁ-]{1,20}$"), name)],
        MIDDLE_NAME:  [MessageHandler(Filters.regex(r"^[а-яёА-ЯЁ-]{1,20}$"), middle_name)],
        PHONE_NUMBER: [MessageHandler(Filters.regex(r"^[0-9]{10}$"), phone_number)],
        INN:          [MessageHandler(Filters.regex(r"^[0-9]{12}$"), inn)],
        CHECK:        [MessageHandler(Filters.text(["Все верно", "Заполнить заявку заново"]), check)]
    },
    fallbacks=[make_handler, MessageHandler(Filters.all, wrong)]
)
