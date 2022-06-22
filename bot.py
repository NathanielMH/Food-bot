from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import city
import restaurants as rest

# Loads CityGraph of Barcelona, OsmnxGraph of the city and list of restaurants from the database.
g2 = city.get_metro_graph()
g1 = city.load_osmnx_graph("street_graph")
g = city.build_city_graph(g1, g2)
restaurants = rest.read()


def build_restaurant_list(list_of_rest: rest.Restaurants) -> str:
    """
    Builds list of restaurants into a string with their names.
    Args:
        list_of_rest: restaurant list to transform

    Returns:
    String with restaurant names skipping a line after each one.
    """
    s = ""
    for i in range(len(list_of_rest)):
        r = list_of_rest[i]
        name = r.name.split(' *')[0]
        s += str(i + 1) + ". " + name + "\n"
    return s


def restaurant_info(r: rest.Restaurant) -> str:
    """
    Gives some restaurant info, which for now is name and address but could fit a description
    if the database is augmented.
    Args:
        r: restaurant from which we need the information

    Returns:
    String with restaurant info.
    """
    name = r.name.split(' *')[0]
    num = int(r.street_num)
    return "Restaurant name: " + name + "\n" + "Street: " + r.street[
        0] + " " + str(num) + "-" + str(
        num + 2) + "\n" + "Neighbourhood: " + r.neighbourhood + "\n" + "District: " + r.district + "\n" + "Phone: " + str(
        r.tel)


def start(update, context) -> None:
    """
    Starts the bot.
    """
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hello! I am your telegram bot. I hope you're hungry! Type /help for guidance on how the bot works.")


def where(update, context) -> None:
    """
    Takes user's location and pickles it into file user_pos.pickle.
    """
    try:
        u_pos = (update.message.location.longitude, update.message.location.latitude)
        context.user_data["user_position"] = u_pos
    except Exception as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please share your location with the bot so it can function correctly.')


def help(update, context) -> None:
    """
    Bot sends help message.
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I am a bot with commands /start, /help, /info, /find, /author and /guide. \n"
             + "/find: this allows you to search for restaurants. Type in a query and it will return a list "
               "of restaurants related to said query. \n "
             + "/info: this gives information on the restaurants you just looked at. Type an index "
               "from 1 to 10 to indicate which restaurant you want information of from the list. \n"
             + "/guide: this gives a map to the restaurant that you have selected from the list using the metro ("
               "possibly). "
             + "Type an index from 1 to 10 to indicate which restaurant you want information of from the list. \n"
             + "/author: this gives you the names of the authors of the bot. \n"
             + "Enjoy!")


def author(update, context) -> None:
    """
    Bot sends message containing author's names.
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Paula Esquerrà and Nathaniel Mitrani")


def find(update, context) -> None:
    """
    Bot asks for input on what the user wants to find and sends a message with the restaurant names that match his
    search. The list is pickled for later use.
    """
    try:
        query = ""
        for i in range(len(context.args)):
            query += str(context.args[i])
        list_of_r = rest.find(query, restaurants)
        context.user_data["recommended_restaurants"] = list_of_r
        answer = build_restaurant_list(list_of_r)
        context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    except IndexError as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Empty query! Please enter a search query'
                                                                        ' after the /find command')
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text='No restaurants match your search! Please try '
                                                                        'again.')


def info(update, context) -> None:
    """
    Bot sends information about the restaurant he has been enquired about.
    """
    try:
        list_num = int(context.args[0]) - 1
        recommended = context.user_data["recommended_restaurants"]
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=restaurant_info(recommended[list_num]))
    except KeyError as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please search for restaurants with the /find command to ask for information.')
    except IndexError as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Invalid index. Either no restaurants matches your search, or you selected an invalid index.')


def guide(update, context) -> None:
    """
    Bot sends a picture of a map from the user's location to the restaurant he asked directions to.
    """
    try:
        list_num = int(context.args[0]) - 1
        recommended = context.user_data["recommended_restaurants"]
        user_pos = context.user_data["user_position"]
        r = recommended[list_num]
        path = city.find_path(g1, g, user_pos, r.coordinates)
        city.plot_path(g, path, "user_plot")
        t = city.time_from_path(g, path)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open("user_plot.png", 'rb'))
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Estimated time of arrival is " + str(t) + " minutes.")
    except IndexError as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Invalid index. Please select an index between 1 and ' + str(
                len(context.user_data["recommended_restaurants"])) + '.')
    except KeyError as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please share your location and ask for restaurant recommendations before using the /guide command.')
    except Exception as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We are experiencing technical difficulties. Please retry.')


# declares a constant with the access token retrieved from token.txt
TOKEN = open('token.txt').read().strip()

# creates objects to work with Telegram
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# indicates that when the bot recieves the command /start, the start function is executed
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.location, where))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('find', find))
dispatcher.add_handler(CommandHandler('info', info))
dispatcher.add_handler(CommandHandler('guide', guide))
dispatcher.add_handler(CommandHandler('author', author))

# starts the bot
updater.start_polling()
updater.idle()
