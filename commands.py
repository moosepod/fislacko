""" Contains the commands for the Fiasco/Slack web service
"""
import random
import re
import logging

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

class MockFirebase(object):
    def __init__(self,data=None):
        self.data = data or {}

    def get(self,path,subpath):
        """ 
>>> MockFirebase({'foo': {'bar': {'quux': True}}}).get('foo','bar')
{'quux': True}
"""
        d = self.data
        for part in path.split('/'):
            d = d.get(part)
            if not d:
                return None
        d = d.get(subpath)
        return d
    
    def put(self,path,subpath,data):
        """ 
>>> unicode(MockFirebase().put('foo','bar',{'quux': True}))
u"{'foo': {'bar': {'quux': True}}}"
        """ 
        d = self.data
        for part in path.split('/'):
            if not d.get(part):
                d[part] = {}
            d = d[part]
        d[subpath] = data 
        # Return self to make testing easier
        return self

    def __unicode__(self):
        return unicode(self.data)

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

    def get_user_id_for_slack_name(self,slack_name):
        """ Return the user with the given slack name, or None if no match. Case insensitive 
>>> Game(MockFirebase({'game': {'users':{'12456': {'name': 'Test', 'slack_name': 'Foo'}}}}),'game').get_user_id_for_slack_name('bar')
>>> Game(MockFirebase({'game': {'users':{'12456': {'name': 'Test', 'slack_name': 'Foo'}}}}),'game').get_user_id_for_slack_name('foo')
'12456'
"""
        for user_id,user in self.users.items():
            if user.get('slack_name').lower() == slack_name.lower():
                return user_id
        return None

    def set_user(self,user_id,slack_name, game_name):
        self.firebase.put('%s/users' % self.path,user_id, {'name': game_name, 'slack_name': slack_name})

    def get_user_dice(self,user_id):
        """ Return all dice for a user """
        return [Die(json=x) for x in self.firebase.get('%s/users/%s' % (self.path,user_id), 'dice')]

    def set_user_dice(self,user_id,dice):
        """ Set the dice for a user. Dice should be a list/tuple of Die objects """
        self.firebase.put('%s/users/%s' % (self.path,user_id), 'dice', [x.to_json() for x in dice])

    def clear(self):
        """ Clear this game on firebase """
        self.firebase.delete(self.path,'users')
        self.firebase.delete(self.path,'dice')

    def take_die_from(self,die,from_user_id):
        """ Take the specifed die from the user with the given id then persist the results. 
>>> Game(MockFirebase({'game': {'users':{'12456': {'dice': [{'c':'black','n':1}], 'name': 'Test', 'slack_name': 'Foo'}}}}),'game').take_die_from(Die(params=['b1']),'12456')
True
>>> Game(MockFirebase({'game': {'users':{'12456': {'dice': [{'c':'black','n':1}], 'name': 'Test', 'slack_name': 'Foo'}}}}),'game').take_die_from(Die(params=['b1']),'12456none')
False
>>> Game(MockFirebase({'game': {'users':{'12456': {'dice': [{'c':'black','n':1}], 'name': 'Test', 'slack_name': 'Foo'}}}}),'game').take_die_from(Die(params=['w1']),'12456')
False
"""
        from_user = self.get_user(from_user_id)
        for i,d in enumerate(from_user.get('dice',[])):
            if die.to_json() == d:
                del from_user['dice'][i]
                self.set_user_dice(from_user_id,from_user['dice']) 
                return True
        return False

    def give_die_to(self,die,to_user_id):
        """ Give the specified die to the specified user. 
>>> Game(MockFirebase({'game': {'users':{'12456': {'dice': [], 'name': 'Test', 'slack_name': 'Foo'}}}}),'game').give_die_to(Die(params=['b1']),'12456')
True
>>> Game(MockFirebase({'game': {'users':{'12456': {'dice': [], 'name': 'Test', 'slack_name': 'Foo'}}}}),'game').give_die_to(Die(params=['b1']),'12456none')
False
"""
        to_user = self.get_user(to_user_id)
        if not to_user:
            return False
        if not to_user.get('dice'):
            to_user['dice'] = []
        to_user['dice'].append(die)
        self.set_user_dice(to_user_id,to_user['dice'])
        return True


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
    for uid,v in users.items():
        player_a.append(u'%s (%s) %s' % (v['name'],v['slack_name'],format_dice_pool(game.get_user_dice(uid))))
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
    user_dice = game.get_user(user_id).get('dice',[])
    for i,d in enumerate(dice):
        if d.number == die.number and d.color == die.color:
            del dice[i]
            game.dice = dice
            user_dice.append(die)
            game.set_user_dice(user_id,user_dice)
            return SlackResponse ("%s claimed %s" % (user_name, die.to_emoji()),True)

    return SlackResponse(u"Could not find a %s" % die)

def give(game,params,user_id,user_name):
    """ Give one of your dice to someone else """
    if len(params) < 2:
        return SlackResponse("Usage: /fiasco die slack_name")
    from_player = game.get_user(user_id)
    if not from_player:
        return SlackResponse("You are not registered as a player. Please type /fiasco register your_game_name")

    # Load up our user and desired die
    slack_name = params[-1]
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

    return SlackResponse(u"%s gave %s to %s" % (user_name,die,slack_name))

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

