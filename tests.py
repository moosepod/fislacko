import unittest

from game import MockFirebase, Game, Die

class MockFirebaseTests(unittest.TestCase):
    def test_get(self):
        mf = MockFirebase({'foo': {'bar': {'quux': True}}})
        self.assertEquals({'quux': True}, mf.get('foo','bar'))

    def test_put(self):
        mf = MockFirebase({})
        mf.put('foo','bar',{'quux': True})
        self.assertEquals({'foo': {'bar': {'quux': True}}},mf.data)

class DieTests(unittest.TestCase):
    def test_default(self):
        self.assertEquals( u':d6-5:',Die(color='white',number=5).to_emoji())
        self.assertEquals( u':d6-1-black:',Die(color='black',number=1).to_emoji())
    
    def test_json(self):
        self.assertEquals(u':d6-3-black:', Die(json={'c':'black','n':'3'}).to_emoji())
    
    def test_roll(self):
        die = Die(color='w',number=1)
        self.assertEquals('white',die.color)
        self.assertEquals(1, die.number)
        new_number = die.roll()
        self.assertEquals(die.number,new_number)

    def test_params(self):
        self.assertEquals(u':d6-1:', Die(params=['w1']).to_emoji())
        self.assertEquals(u':d6-3-black:',Die(params=['b3']).to_emoji())
        self.assertEquals(u':d6-6:', Die(params=['white 6']).to_emoji())
        self.assertEquals(u':d6-1-black:',Die(params=['black 1']).to_emoji())

    def test_to_json(self):
        self.assertEquals( {'c': 'white', 'n': 1},Die(params=['w1']).to_json())

    def test_unicode(self):
        self.assertEquals(u'black 2', unicode(Die(params=['b2'])))

class GameTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(MockFirebase({'game': {'users':{'12456': {'name': 'Test', 'slack_name': 'Bar'}}}}),'game')
    
    def test_format_dice_pool(self):
        self.assertEquals(u':d6-1: :d6-5-black: :d6-6-black:',  self.game.format_dice_pool((Die(number=5,color='black'),Die(number=1,color='white'),Die(number=6,color='black'))))

    def test_get_user_id_for_slack_name(self):
        self.assertEquals(None,self.game.get_user_id_for_slack_name('foo'))
        self.assertEquals(u'12456', self.game.get_user_id_for_slack_name('bar'))

    def test_take_die_from(self):
        self.game.set_user_dice('12456',[Die(params=['b1'])])
        self.assertTrue(self.game.take_die_from(Die(params=['b1']),'12456'))
        self.assertFalse(self.game.take_die_from(Die(params=['b1']),'12456none'))
        self.assertFalse(self.game.take_die_from(Die(params=['w1']),'12456'))

    def test_give_die_to(self):
        self.assertTrue(self.game.give_die_to(Die(params=['b1']),'12456'))

if __name__ == '__main__':
    unittest.main()

