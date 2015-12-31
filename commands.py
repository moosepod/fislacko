""" Contains the commands for the Fiasco/Slack web service
"""
import random
import re

class SlackResponse(object):
    def __init__(self,text,in_channel=False):
        self.text = text
        if in_channel:
            self.response_type='in_channel'
        else:
            self.response_type='ephemeral'

    def to_json(self):
        return {'text': self.text, 'response_type': self.response_type}

class InvalidDie(Exception):
    pass

class Die(object):
    DIE_RANGE = (1,2,3,4,5,6)
    COLORS = ('white','black')
    RX = re.compile('^([wb]|white|black)\s?(\d)$')
    def __init__(self,color=None,number=None,json=None,params=None):
        """ Color is white or black. Number is 1-6. Json expects {'c','n'} 
        >>> Die(color='white',number=5).to_emoji()
        u':d6-5:'
        >>> Die(color='black',number=1).to_emoji()
        u':d6-1-black:'
        >>> Die(json={'c':'black','n':'3'}).to_emoji()
        u':d6-3-black:'
        >>> Die(params=['w1']).to_emoji()
        u':d6-1:'
        >>> Die(params=['b3']).to_emoji()
        u':d6-3-black:'
        >>> Die(params=['white 6']).to_emoji()
        u':d6-6:'
        >>> Die(params=['black 1']).to_emoji()
        u':d6-1-black:'
"""
        if json:
            color = json.get('c','no color')
            number = json.get('n','no number')
        if params:
            pt = ' '.join(params)
            m = Die.RX.match(pt.lower())
            if not m:
                raise InvalidDie('Invalid die name %s' % pt)
            color,number = m.group(1), m.group(2)
        
        self.color = color
        try:
            self.number = int(number)
        except ValueError:
            raise InvalidDie('Invalid number for die: %s' % number)
        
        if self.color == 'w': self.color = 'white'
        if self.color == 'b': self.color = 'black' 
        if self.number not in Die.DIE_RANGE:
            raise InvalidDie('Die number %s not in range %s' % (self.number, Die.DIE_RANGE))
        if self.color not in Die.COLORS:
            raise InvalidDie('Invalid color %s' % self.color)
    
    def to_emoji(self):
        extra = ''
        if self.color == 'black':
            extra = '-black'
        return u':d6-%d%s:' % (self.number,extra)

def reset_game(game,path,params,user_id,user_name):
    """ Reset the game """
    if len(params) == 1 and params[0].lower() == 'yes':
        game.delete(path,'users')
        game.delete(path,'dice')
        return SlackResponse('%s has reset the game.' % user_name)
    
    return SlackResponse('To reset, pass in confirm as the parameter')   

def register(game,path,params,user_id,user_name):
    """ Register the logged in user as a given character """
    # Take in name
    # Store name
    if not len(params):
        return SlackResponse('Please provide the name you will go by.')
    name = ' '.join(params)
    game.put('%s/users' % path,user_id,{'name':name,'slack_name': user_name})
    return SlackResponse('%s is now registered as %s' % (user_name,name),True)

def status(game,path,params,user_id,user_name):
    """ Send game status to channel """
    player_a = []
    users = game.get(path,'users')
    for v in users.values():
        player_a.append(u'%s (%s)' % (v['name'],v['slack_name']))
    return SlackResponse("""Players: %s

%s""" % (u"\n".join(player_a),
               format_dice_pool(game.get(path,'dice'))),True)

def claim(game,path,params,user_id,user_name):
    """ Claim a specific die """
    # Take color + number
    # Verify die
    # take die
    # Print status
    if len(params) != 2:
        return SlackResponse("Usage: /fiasco claim color number")
    
    # Validate
    color,number = [x.lower() for x in params]
    if color not in ('white','black','w','b'):
        return SlackResponse("Color needs to be white, black, w or b")
    try:
        number_int = int(number)
        if number_int not in (1,2,3,4,5,6):
            return SlackResponse('Number needs to be 1-6')
    except ValueError:
        return SlackResponse('Number needs to be 1-6')
    
    # Find die
    dice = game.get(path,'dice')
    user_dice = game.get(u'users/%s' % user_id,'dice') or {}
    if color[0] == 'w':
        color = 'white'
    else:
        color = 'black'
    if not user_dice.get(color): user_dice['color'] = []
    for i,d in enumerate(dice.get(color,[])):
        if str(d) == number:
            del dice[color][i]
            game.put(path,'dice',dice)
            user_dice['color'].append(d)
            game.put(u'users/user_id','dice',user_dice)
            return SlackResponse ("%s claimed %s %s" % (user_name, color, d),True)

    return SlackResponse("Could not find a %s %s" % (color, number_int))


def give(game,path,params,user_id,user_name):
    """ Give one of your dice to someone else """
    return SlackResponse("%s gave dice" % (user_name),True)

def roll(game,path,params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    return SlackRespones("%s rolled: " % user_name,True)

def roll_pool(game,path,params,user_id,user_name):
    """ Reroll the central dice pool. Should be two black and two white dice for each user """
    dice = {'black': [],'white': []}
    user_count = len(game.get(path,'users'))
    for l in (dice['black'],dice['white']):
        for i in range((user_count*2)):
            l.append(random.randint(1,6))
    game.put(path,'dice',dice)
    return SlackResponse("""Pool recreated.

%s
""" % format_dice_pool(dice),True)

numbers=['zero','one','two','three','four','five','six']

def format_dice_pool(dice):
    """ >>> format_dice_pool(Die(number=5,color='black'),Die(number=1,color='white'),Die(number=6,color='black'))
        u':d6-5-black: :d6-1: :d6-6-black:'
    """
    if not dice:
        return ""
    return u"""%s %s
""" % (' '.join([x.to_emoji() for x in dice if x.color == 'white'])
       ' '.join([x.to_emoji() for x in dice if x.color == 'black'])

def spend(game,path,params,user_id,user_name):
    """ Let a user spend one of their dice """
    # Take color and number
    # Verify
    return SlackResponse("Spent")


if __name__ == "__main__":
    import doctest
    doctest.testmod()

