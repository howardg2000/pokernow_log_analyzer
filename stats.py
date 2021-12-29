import pandas as pd
import re

class Game:
    def __init__(self, user):
        self.user = user
        self.playerInfo = {}
        self.hands = []
        self.currentHand = None

    def addApprovedPlayer(self, player, chips):
        if player in self.playerInfo:
            info = self.playerInfo[player]
            info.newBuy(chips)
        else:
            self.playerInfo[player] = playerStats(player, chips)

    def startNewHand(self, dealer, num):
        self.endHand()
        self.currentHand = Hand(dealer, num)

    def endHand(self):
        if self.currentHand is not None:
            self.hands.append(self.currentHand)

    def verifyStacks(self, stacks):
        # TODO: finish
        self.currentHand.initializeStacks(stacks)
        for player, chips in stacks.items():
            self.playerInfo[player].chips = chips
            # if self.playerInfo[player]['chips'] != chips:
            #     raise ValueError("WRONG STACK SIZES")

    def addAction(self, player, action, amount=0):
        self.currentHand.addAction(player, action, amount)
        

class playerStats:
    def __init__(self, player, chips):
        self.player = player
        self.chips = chips
        self.numBuys = 1
        self.buyAmounts = [chips]
        self.outAmounts = []

    def newBuy(self, chips):
        self.numBuys += 1
        self.buyAmounts.append(chips)
        self.chips = chips

    def leaveGame(self, chips):
        self.outAmounts.append(chips)
        self.chips = 0

class Hand:
    def __init__(self, dealer, handNumber):
        self.dealer = dealer
        self.handNumber = handNumber
        self.stacks = None

        self.preflopActions = []
        self.flopActions = []
        self.turnActions = []
        self.riverActions = []
        
        self.flop = None
        self.turn = None
        self.river = None

        self.holeCards = {}

    def initializeStacks(self, stacks):
        self.stacks = stacks

    def addAction(self, player, action, amount=0):
        currentAction = Action(player, action, amount)
        if self.flop is None:
            self.preflopActions.append(currentAction)
        elif self.turn is None:
            self.flopActions.append(currentAction)
        elif self.river is None:
            self.turnActions.append(currentAction)
        else:
            self.riverActions.append(currentAction)
    
    def dealBoard(self, cards):
        if self.flop is None:
            self.flop = cards
        elif self.turn is None:
            self.turn = cards
        else:
            self.river = cards


class Action:
    def __init__(self, player, action, amount):
        self.player = player
        self.action = action
        self.amount = amount

    def __str__(self) -> str:
        return f'{self.player} {self.action} {self.amount}'

def parseLog(filename, user):
    game = Game(user)
    df = pd.read_csv(filename)
    for row in df[::-1].itertuples():
        desc = row.entry
        time = row.at
        if desc.startswith("The admin approved the player "):
            # The admin approved the player "user @asdf" participation with a stack of x.
            player = desc.split('"')[1]
            chips = int(desc.split()[-1][:-1])
            game.addApprovedPlayer(player, chips)
        elif desc.startswith("-- starting hand "):
            if 'dead button' in desc:
                dealer = None
            else:
                dealer = desc.split('"')[1]
            numberMatch = re.search(r'#(\d+)', desc)
            handNumber = numberMatch.group(1)
            game.startNewHand(dealer, handNumber)
        elif desc.startswith("-- ending hand"):
            pass
        elif desc.startswith("Player stacks:"):
            # regex to get (player, stack) tuples. Matches of form
            # '"username" (chips)'
            stacks = re.findall(r'"([^"]*)" \((\d+)\)', desc)
            playerStacks = {}
            for stack in stacks:
                playerStacks[stack[0]] = int(stack[1])
            game.verifyStacks(playerStacks)

        elif "posts a small blind" in desc:
            player = desc.split('"')[1]
            blind = int(desc.split()[-1])
            game.currentHand.addAction(player, "smallBlind", blind)
        elif "posts a big blind" in desc:
            player = desc.split('"')[1]
            blind = int(desc.split()[-1])
            game.currentHand.addAction(player, "bigBlind", blind)
        elif "posts a straddle" in desc:
            player = desc.split('"')[1]
            straddle = int(desc.split()[-1])
            game.currentHand.addAction(player, "straddle", straddle)
        elif "posts a missing small blind" in desc:
            player = desc.split('"')[1]
            blind = int(desc.split()[-1])
            game.currentHand.addAction(player, "missingSmallBlind", blind)
        elif "posts a missed big blind" in desc:
            player = desc.split('"')[1]
            blind = int(desc.split()[-1])
            game.currentHand.addAction(player, "missingBigBlind", blind)

        elif desc.endswith("folds"):
            player = desc.split('"')[1]
            game.currentHand.addAction(player, "fold")
        elif desc.endswith("checks"):
            player = desc.split('"')[1]
            game.currentHand.addAction(player, "check")

        elif desc.endswith("go all in"):
            player = desc.split('"')[1]
            if "raises to" in desc:
                amount = re.search(r'raises to (\d+)', desc).group(1)
                game.currentHand.addAction(player, "raiseAllIn", int(amount))
            elif "calls" in desc:
                amount = re.search(r'calls (\d+)', desc).group(1)
                game.currentHand.addAction(player, "callAllIn", int(amount))
            elif "bets" in desc:
                amount = re.search(r'bets (\d+)', desc).group(1)
                game.currentHand.addAction(player, "raiseAllIn", int(amount))
        elif "raises to" in desc:
            player = desc.split('"')[1]
            amount = re.search(r'raises to (\d+)', desc).group(1)
            game.currentHand.addAction(player, "raise", int(amount))
        elif "calls" in desc:
            player = desc.split('"')[1]
            amount = re.search(r'calls (\d+)', desc).group(1)
            game.currentHand.addAction(player, "call", int(amount))
        elif "bets" in desc:
            player = desc.split('"')[1]
            amount = re.search(r'bets (\d+)', desc).group(1)
            game.currentHand.addAction(player, "raise", int(amount))

        elif desc.startswith("Flop: "):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            cards = cardsString[1:-1].split(', ')
            game.currentHand.dealBoard(cards)
        elif desc.startswith("Turn: "):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            game.currentHand.dealBoard(cardsString[1:-1])
        elif desc.startswith("River: "):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            game.currentHand.dealBoard(cardsString[1:-1])

        elif "shows a" in desc:
            player = desc.split('"')[1]
            cardString = re.search(r'shows a ([^.]*).', desc).group(1)
            cards = cardString.split(', ')
            game.currentHand.holeCards[player] = cards
        elif "Your hand is " in desc:
            cardString = re.search(r'Your hand is (.*)', desc).group(1)
            cards = cardString.split(', ')
            game.currentHand.holeCards[user] = cards
        
    game.endHand()
    return game
    

def main():
    filename = 'cur2.csv'
    user = 'how'
    game = parseLog(filename, user)
    for hand in game.hands:
        print(hand.handNumber, hand.flop, hand.turn, hand.river)
        print(hand.holeCards)
        for action in hand.preflopActions:
            print(action)

if __name__=="__main__":
    main()
