# bot-parser
In this project, a bot job parser was created for the Telegram messenger. The database 'base.db' has a list of channels that the bot will check and forward to our job chat using user's keys.

The bot has a main search criterion, in this implemented code, the main selection of vacancies takes place in the field of 'Marketing'. Next, the user can add additional filtering for the search by clicking on the 'keys' button, the bot will already select vacancies not only in the field of marketing, but already using the added user keys. The user and his keys are saved to the 'marketing_base' database, which allows you to save the added keys by the user and in case of exiting the messenger or stopping working with the bot, the keys will be saved in the list, the user will not need to add them again.

Databases have been implemented in sqlite. SQLite is an amazing library embedded in the application that uses it. Being a file database, it provides an excellent set of tools for simpler (compared to server databases) processing of any kind of data.

When an application uses SQLite, their communication is performed using functional and direct calls to files containing data (for example, SQLite databases), rather than some kind of interface, which increases the speed and performance of operations.
