""" Contains the commands for the Fiasco/Slack web service
"""
import random
import re
import logging

from utils import SlackResponse,InvalidDie,MockFirebase,Die,Game

def reset_game(game,params,user_id,user_name):
    """ Reset the game data """
    if len(params) == 1 and params[0].lower() == 'confirm':
        game.clear()
        return SlackResponse('%s has reset the game.' % user_name)
    
    return SlackResponse('To reset, pass in confirm as the parameter')   

def register(game,params,user_id,user_name):
    """ Register the logged in user as a given character """
    # Take in name
    # Store name
    if not len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    game.set_user(user_id,user_name,name)
    
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)

def status(game,params,user_id,user_name):
    """ Send game status to channel """
    player_a = []
    users = game.users or []
    if not users:
        player_a.append('No users registered')
    else:
        for uid,v in users.items():
            player_a.append(u'%s (%s) %s' % (v['name'],v['slack_name'],format_dice_pool(game.get_user_dice(uid))))
    return SlackResponse("""%s

%s""" % (u"\n".join(player_a),
               format_dice_pool(game.dice)),True)

def claim(game,params,user_id,user_name):
    """ Claim a specific die """
    if len(params) < 1:
        return SlackResponse("Usage: /fiasco claim color number")
    
    # Validate
    try:
        die = Die(params=params)
    except InvalidDie:
        return SlackResponse('Format is w5 or white 5 (or b1 or black 1')
    
    # Find die
    dice = game.dice
    user_dice = game.get_user_dice(user_id) or []
    for i,d in enumerate(dice):
        if d.to_json() == die.to_json():
            del dice[i]
            game.dice = dice
            user_dice.append(die)
            game.set_user_dice(user_id,user_dice)
            return SlackResponse ("%s claimed %s.\nPool: %s" % (user_name, die.to_emoji(),format_dice_pool(dice) or 'Empty'),True)

    return SlackResponse(u"Could not find a %s" % die)

def give(game,params,user_id,user_name):
    """ Give one of your dice to someone else """
    if len(params) < 2:
        return SlackResponse("Usage: /fiasco die slack_name")
    from_player = game.get_user(user_id)
    if not from_player:
        return SlackResponse("You are not registered as a player. Please type /fiasco register your_game_name")

    # Load up our user and desired die
    slack_name = params[-1].replace('@','') # Allow use of @
    to_player_id = game.get_user_id_for_slack_name(slack_name)
    if not to_player_id:
        return SlackResponse('No player found with slack name "%s"' % slack_name)
    try:
        die = Die(params=params[0:-1])
    except InvalidDie:
        return SlackResponse('Format is w5 or white 5 (or b1 or black 1)')
    if not game.take_die_from(die,user_id):
        return SlackResponse(u'%s does not have a %s' % (slack_name, die))
    game.give_die_to(die,to_player_id)
    return SlackResponse(u"%s gave %s to %s" % (user_name,die.to_emoji(),slack_name),True)

def roll(game,params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    return SlackResponse("Not implemented")

def pool(game,params,user_id,user_name):
    """ Output the dice pool. If "roll" is the first parameter, reroll. Should be two black and two white dice for each user """
    dice = game.dice
    if params == ['roll']:
        # Reroll dice
        dice = []
        user_count = len(game.users)
        if not user_count:
            return SlackResponse("No registered users so no dice rolled. /fiasco register Your Name to register yourself.")
        for color in ('black','white'):
            for i in range((user_count*2)):
                dice.append(Die(color=color,number=random.randint(1,6)))
        game.dice = dice
 
        # Clear dice for users
        for user_id in game.users.keys():
            game.set_user_dice(user_id,[])
 
    return SlackResponse(format_dice_pool(dice) or "No dice in pool",True)

def format_dice_pool(dice):
    """ 
>>> format_dice_pool((Die(number=5,color='black'),Die(number=1,color='white'),Die(number=6,color='black')))
u':d6-1: :d6-5-black: :d6-6-black:'
    """
    if not dice:
        return ""
    return u"%s %s"% (' '.join([x.to_emoji() for x in dice if x.color == 'white']),
       ' '.join([x.to_emoji() for x in dice if x.color == 'black']))

def spend(game,params,user_id,user_name):
    """ Let a user spend one of their dice """
    # Take color and number
    # Verify
    return SlackResponse("Not implemented.")


if __name__ == "__main__":
    import doctest
    doctest.testmod()

