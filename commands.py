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
    """ Abstracts a D6 that can be white or black """
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
        >>> Die(params=['w1']).to_json()
        {'c': 'white', 'n': 1}
        >>> unicode(Die(params=['b2']))
        u'black 2'
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
    
    def to_json(self):
        return {'n': self.number,'c': self.color}

    def to_emoji(self):
        extra = ''
        if self.color == 'black':
            extra = '-black'
        return u':d6-%d%s:' % (self.number,extra)

    def __unicode__(self):
        return u'%s %s' % (self.color, self.number)

class Game(object):
    def __init__(self,firebase,path):
        self.firebase = firebase
        self.path = path
    
    @property
    def dice(self):
        return [Die(json=x) for x in self.firebase.get(self.path,'dice') or []]

    @dice.setter
    def dice(self,value):
        self.firebase.put(self.path,'dice',[x.to_json() for x in value])
    
    @property
    def users(self):
        return self.firebase.get(self.path,'users') or {}

    def get_user(self,user_id):
        return self.firebase.get('%s/users' % self.path, user_id) or {}

    def set_user(self,user_id,slack_name, game_name):
        self.firebase.put('%s/users' % self.path,user_id, {'name': game_name, 'slack_name': slack_name})

    def set_user_dice(self,user_id,dice):
        """ Set the dice for a user. Dice should be a list/tuple of Die objects """
        self.firebase.put('%s/users/%s' % (self.path,user_id), 'dice', [x.to_json() for x in dice])

    def clear(self):
        """ Clear this game on firebase """
        self.firebase.delete(self.path,'users')
        self.firebase.delete(self.path,'dice')

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
    users = game.users
    for v in users.values():
        player_a.append(u'%s (%s)' % (v['name'],v['slack_name']))
    return SlackResponse("""Players: 
%s

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
    user_dice = game.get_user(user_id).get('dice',{})
    for i,d in enumerate(dice):
        if d.number == die.number and d.color == die.color:
            del dice[i]
            game.dice = dice
            game.set_user_dice(user_id,user_dice)
            return SlackResponse ("%s claimed %s" % (user_name, die.to_emoji()),True)

    return SlackResponse(u"Could not find a %s" % die)

def give(game,params,user_id,user_name):
    """ Give one of your dice to someone else """
    return SlackResponse("Not implemented.")

def roll(game,params,user_id,user_name):
    """ Roll a user's dice and show the sum """
    return SlackResponse("Not implemented")

def roll_pool(game,params,user_id,user_name):
    """ Reroll the central dice pool. Should be two black and two white dice for each user """
    dice = []
    user_count = len(game.users)
    if not user_count:
        return SlackResponse("No registered users so no dice rolled. /fiasco register Your Name to register yourself.")
    for color in ('black','white'):
        for i in range((user_count*2)):
            dice.append(Die(color=color,number=random.randint(1,6)))
    game.dice = dice

    return SlackResponse("""Pool recreated.

%s
""" % format_dice_pool(dice),True)

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

