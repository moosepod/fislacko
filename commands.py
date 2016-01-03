""" Contains the commands for the Fiasco/Slack web service
"""
import random
import re
import logging

from game import SlackResponse,InvalidDie,Die,Game

def reset_game(game,params,user_id,user_name):
    """ Reset the game data """
    if len(params) == 1 and params[0].lower() == 'confirm':
        game.clear()
        return SlackResponse('%s has reset the game.' % user_name)
    
    return SlackResponse('To reset, pass in confirm as the parameter')   

def setup(game,params,user_id,user_name):
    setup = game.setup
    if len(params) > 0:
        if params[0] == 'add':
            setup.append(' '.join(params[1:]))
        elif params[0] in ('delete','remove','del'):
            try:
                del setup[int(params[1])]
            except ValueError:
                pass
        game.setup = setup

    if not len(setup):
        return SlackResponse("Game has no setup.",True)
    return SlackResponse('\n'.join(["%d) %s" % (i,v) for i,v in enumerate(setup)]),True)

def register(game,params,user_id,user_name):
    """ Register the logged in user as a given character """
    # Take in name
    # Store name
    if not len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    game.set_user(user_id,user_name,name)
    
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)

def unregister(game,params,user_id,user_name):
    """ Unregister the current user or a named user """
    if len(params):
        unreg_name = ' '.join(params)
        unreg_id = game.get_user_id_for_slack_name(unreg_name)
    else:
        unreg_name = user_name
        unreg_id = user_id

    game.unregister(unreg_id)
    return SlackResponse("%s is longer registered" % unreg_name,True)

def status(game,params,user_id,user_name):
    """ Send game status to channel """
    player_a = []
    users = game.users or []
    if not users:
        player_a.append('No users registered')
    else:
        for uid,v in users.items():
            try:
                player_a.append(u'%s (%s) %s' % (v['name'],v['slack_name'],game.format_dice_pool(game.get_user_dice(uid) or [])))
            except Exception, e:
                logging.error(e)
    return SlackResponse("""%s

%s""" % (u"\n".join(player_a),
               game.format_dice_pool(game.dice)),True)

def take(game,params,user_id,user_name):
    """ Take a specific die from the pool """
    if len(params) < 1:
        return SlackResponse("Usage: /fiasco take color number")
    
    # Validate
    try:
        die = Die(params=params)
    except InvalidDie:
        return SlackResponse('Format is w5 or white 5 (or b1 or black 1')
    
    # Find die
    user_dice = game.get_user_dice(user_id) or []
    if game.take_die_from_pool(die):
        user_dice.append(die)
        game.set_user_dice(user_id,user_dice)
        return SlackResponse ("%s claimed %s.\nPool: %s" % (user_name, die.to_emoji(),game.format_dice_pool(game.dice) or 'Empty'),True)

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
    if slack_name == 'pool':
        to_player_id = 'pool'
    else:
        to_player_id = game.get_user_id_for_slack_name(slack_name)
    if not to_player_id:
        return SlackResponse('No player found with slack name "%s"' % slack_name)
    try:
        die = Die(params=params[0:-1])
    except InvalidDie:
        return SlackResponse('Format is w5 or white 5 (or b1 or black 1)')
    if not game.take_die_from(die,user_id):
        return SlackResponse(u'%s does not have a %s' % (user_name, die))
    if slack_name == 'pool':
        dice = game.dice
        dice.append(die)
        game.dice = dice
    else:
        game.give_die_to(die,to_player_id)
    return SlackResponse(u"%s gave %s to %s" % (user_name,die.to_emoji(),slack_name),True)

def roll(game,params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    dice = game.get_user_dice(user_id)
    if not dice:
        return SlackResponse("You have no dice.")
    dx = sum([x.roll() for x in dice if x.color == 'white']) - sum([x.roll() for x in dice if x.color == 'black'])
    rolled = game.format_dice_pool(dice)
    if dx > 0:
        return SlackResponse("%s rolled %s totalling white %d" % (user_name,rolled,dx),True)
    elif dx < 0:
        return SlackResponse("%s rolled %s totalling black %d" % (user_name,rolled,abs(dx)),True)
    return SlackResponse("%s rolled %s totalling 0." % (user_name,rolled),True)   

def pool(game,params,user_id,user_name):
    """ Output the dice pool. Based on parameters, optionally reset or reroll. """
    dice = game.dice
    if params == ['reset']:
        # Reset dice
        dice = []
        user_count = len(game.users)
        if not user_count:
            return SlackResponse("No registered users so no dice rolled. /fiasco register Your Name to register yourself.")
        for color in ('black','white'):
            for i in range((user_count*2)):
                dice.append(Die(color=color,number=random.randint(1,6)))
        game.dice = dice
    elif params == ['reroll']:
        # Reroll dice still in pool
        dice = game.dice
        for die in dice:
            die.roll()
        game.dice = dice
 
    return SlackResponse(game.format_dice_pool(dice) or "No dice in pool",True)

def spend(game,params,user_id,user_name):
    """ Let a user spend one of their dice """
    dice = game.get_user_dice(user_id)
    try:
        die = Die(params=params)
    except InvalidDie:
        return SlackResponse('Format is w5 or white 5 (or b1 or black 1)')
    
    for i,d in enumerate(dice):
        if die.to_json() == d.to_json():
            del dice[i]
            game.set_user_dice(user_id,dice)
            return SlackResponse("%s spent %s" % (user_name, die.to_emoji()),True)
       
    return SlackResponse("You don't have a %s" % die.to_emoji())

