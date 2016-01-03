import random
import re
import logging
import pymongo

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

class GameState(object):
    def __init__(self,data=None):
        self.data = data or {}

    def save(self,game_id):
        client = pymongo.MongoClient()
        db = client.fislacko
        self.data['_id'] = game_id
        db.games.replace_one({'_id': game_id},self.data,upsert=True)
        
    def load(self,game_id):
        client = pymongo.MongoClient()
        db = client.fislacko
        self.data = db.games.find_one({'_id': game_id}) or {}

    def get(self,path,subpath):
        d = self.data
        for part in path.split('/'):
            d = d.get(part)
            if not d:
                return None
        d = d.get(subpath)
        return d

    def put(self,path,subpath,data):
        d = self.data
        for part in path.split('/'):
            if not d.get(part):
                d[part] = {}
            d = d[part]
        d[subpath] = data

    def delete(self,path,subpath):
        d = self.data
        for part in path.split('/'):
            d = d.get(part)
            if not d:
                return None
        try:
            del d[subpath]
        except KeyError:
            pass

    def __unicode__(self):
        return unicode(self.data)

class Die(object):
    """ Abstracts a D6 that can be white or black """
    DIE_RANGE = (1,2,3,4,5,6)
    COLORS = ('white','black')
    RX = re.compile('^([wb]|white|black)\s?(\d)$')
    def __init__(self,color=None,number=None,json=None,params=None):
        """ Color is white or black. Number is 1-6. Json expects {'c','n'}"""
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
    
    def roll(self):
        """ Roll a number for this die, storing it and returning it """
        n = random.randint(1,6)
        self.number =  n
        return n

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
    def __init__(self,game_state):
        self.game_state = game_state
        self.path = ''

    def format_dice_pool(self,dice):
        """ Take a list/tuple of dice and return them sorted into white and black dice, as emoji """
        if not dice:
            return ""
        return u"%s %s"% (' '.join([x.to_emoji() for x in dice if x.color == 'white']),
            ' '.join([x.to_emoji() for x in dice if x.color == 'black']))

    @property
    def dice(self):
        return [Die(json=x) for x in self.game_state.get(self.path,'dice') or []]

    @dice.setter
    def dice(self,value):
        self.game_state.put(self.path,'dice',[x.to_json() for x in value])

    @property
    def setup(self):
        return self.game_state.get(self.path,'setup') or []

    @setup.setter
    def setup(self,value):
        self.game_state.put(self.path,'setup',value)

    @property
    def users(self):
        return self.game_state.get(self.path,'users') or {}

    def get_user(self,user_id):
        return self.game_state.get('%s/users' % self.path, user_id) or {}

    def get_user_id_for_slack_name(self,slack_name):
        """ Return the user with the given slack name, or None if no match. Case insensitive """
        for user_id,user in self.users.items():
            if user.get('slack_name').lower() == slack_name.lower():
                return user_id
        return None

    def unregister(self,user_id):
        self.game_state.delete(u'%s/users' % (self.path,),user_id)
        
    def set_user(self,user_id,slack_name, game_name):
        self.game_state.put('%s/users' % self.path,user_id, {'name': game_name, 'slack_name': slack_name})

    def get_user_dice(self,user_id):
        """ Return all dice for a user """
        return [Die(json=x) for x in self.game_state.get('%s/users/%s' % (self.path,user_id), 'dice') or []]

    def set_user_dice(self,user_id,dice):
        """ Set the dice for a user. Dice should be a list/tuple of Die objects """
        self.game_state.put('%s/users/%s' % (self.path,user_id), 'dice', [x.to_json() for x in dice])

    def clear(self):
        """ Clear this game on.game_state """
        self.game_state.delete(self.path,'users')
        self.game_state.delete(self.path,'dice')
        self.game_state.delete(self.path,'setup')

    def take_die_from_pool(self,die):
        """ Take the specified die from the pool and persist results. Return True if successful, False if die not in pool """
        dice = self.dice
        for i,d in enumerate(dice):
            if d.to_json() == die.to_json():
                del dice[i]
                self.dice = dice
                return True
        return False

    def take_die_from(self,die,from_user_id):
        """ Take the specifed die from the user with the given id then persist the results."""
        dice = self.get_user_dice(from_user_id)
        for i,d in enumerate(dice):
            if die.to_json() == d.to_json():
                del dice[i]
                self.set_user_dice(from_user_id,dice)
                return True
        return False

    def give_die_to(self,die,to_user_id):
        """ Give the specified die to the specified user."""
        dice = self.get_user_dice(to_user_id) or []
        dice.append(die)
        self.set_user_dice(to_user_id,dice)
        return True
