from __future__ import annotations

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "ru", "az")

TRANSLATIONS = {
    "en": {
        "forward": "Forwarding to the manager",
        "cant_help": "Can't help with that here, sorry.",
        "trouble": "Having trouble understanding that, can you try again?",
        "limit_reached": "This is taking a while, let me get a person to help you directly.",
        "cancelled": "No worries, cancelled that. Anything else I can help with?",
        "ask_location": "Which location did you mean, {names}?",
        "ask_missing_booking_info": "What else do you need to tell me, party size, date or time?",
        "nothing_free": "Nothing free at that time, want to try a different time?",
        "ask_name": "What name should I put it under?",
        "confirm_booking": (
            "Just to confirm: table for {party_size} at {location}, {date} at {time}, "
            "{area} seating, under {name}. Shall I book it, or is there anything to change?"
        ),
        "booked": (
            "Booked. {restaurant}, {address}. {date} at {time}, {area} seating, "
            "party of {party_size}, under {name}."
        ),
        "booking_failed": "Couldn't book that, {error}.",
        "ask_extend_info": (
            "Who's the reservation under, and for what date? Need your name to confirm it's you."
        ),
        "extend_failed": "Couldn't extend that, {error}.",
        "extended": "Extended, {name}'s table now runs {duration} minutes.",
    },
    "ru": {
        "forward": "Передаю менеджеру.",
        "cant_help": "Не могу помочь с этим здесь, извините.",
        "trouble": "Не совсем понял, можете повторить?",
        "limit_reached": "Это затянулось, я подключу сотрудника.",
        "cancelled": "Хорошо, отменено. Могу чем-то ещё помочь?",
        "ask_location": "Какой филиал вы имеете в виду, {names}?",
        "ask_missing_booking_info": "Что ещё уточнить: количество гостей, дату или время?",
        "nothing_free": "На это время нет свободных столов, хотите другое время?",
        "ask_name": "На какое имя оформить?",
        "confirm_booking": (
            "Подтвердите, пожалуйста: столик на {party_size} чел. в {location}, {date} в {time}, "
            "зона {area}, на имя {name}. Оформляю бронь или что-то изменить?"
        ),
        "booked": (
            "Забронировано. {restaurant}, {address}. {date} в {time}, зона {area}, "
            "на {party_size} чел., на имя {name}."
        ),
        "booking_failed": "Не получилось забронировать: {error}.",
        "ask_extend_info": (
            "На чьё имя бронь и на какую дату? Назовите имя, чтобы подтвердить, что это вы."
        ),
        "extend_failed": "Не получилось продлить: {error}.",
        "extended": "Продлено, столик на имя {name} теперь на {duration} минут.",
    },
    "az": {
        "forward": "Menecerə yönləndirirəm.",
        "cant_help": "Bununla burada kömək edə bilmirəm, üzr istəyirəm.",
        "trouble": "Tam anlamadım, bir də yaza bilərsiniz?",
        "limit_reached": "Bu bir az uzun çəkdi, sizi işçiyə yönləndirirəm.",
        "cancelled": "Problem deyil, ləğv olundu. Başqa nə ilə kömək edə bilərəm?",
        "ask_location": "Hansı filialı nəzərdə tutursunuz, {names}?",
        "ask_missing_booking_info": "Daha nə lazımdır: neçə nəfər, tarix, yoxsa saat?",
        "nothing_free": "O vaxt üçün boş masa yoxdur, başqa vaxt sınayaq?",
        "ask_name": "Hansı ad üzərinə yazım?",
        "confirm_booking": (
            "Təsdiq üçün: {location} filialında {party_size} nəfərlik masa, {date} tarixində "
            "saat {time}, {area} bölməsi, {name} adına. Sifarişi təsdiqləyimmi, yoxsa nəyisə "
            "dəyişək?"
        ),
        "booked": (
            "Sifariş edildi. {restaurant}, {address}. {date}, saat {time}, {area} bölməsi, "
            "{party_size} nəfər, {name} adına."
        ),
        "booking_failed": "Sifariş alınmadı: {error}.",
        "ask_extend_info": "Sifariş kimin adınadır və hansı tarixə? Təsdiq üçün adınızı deyin.",
        "extend_failed": "Uzatmaq mümkün olmadı: {error}.",
        "extended": "Uzadıldı, {name} adına masa indi {duration} dəqiqə davam edir.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    templates = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = templates.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE][key]
    return template.format(**kwargs)
