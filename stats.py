import pandas as pd
import re
from collections import defaultdict

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
            self.playerInfo[player] = PlayerInfo(player, chips)

    def leavesGame(self, player, chips):
        self.playerInfo[player].leaveGame(chips)

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

    def addAction(self, player, action, amount=0, time=None):
        self.currentHand.addAction(player, action, amount, time)
        

class PlayerInfo:
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

    def __str__(self) -> str:
        return f'Player: {self.player}, chips: {self.chips}, numBuys: {self.numBuys}, buyAmounts: {self.buyAmounts}, outAmounts: {self.outAmounts}'

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
        self.secondFlop = None
        self.secondTurn = None
        self.secondRiver = None

        self.holeCards = {}
        self.winners = []
        self.winningAmounts = []
        self.winningCombination = []
        self.winningType = []

    def initializeStacks(self, stacks):
        self.stacks = stacks

    def addAction(self, player, action, amount=0, time=None):
        currentAction = Action(player, action, amount)
        if self.flop is None:
            self.preflopActions.append(currentAction)
        elif self.turn is None:
            self.flopActions.append(currentAction)
        elif self.river is None:
            self.turnActions.append(currentAction)
        else:
            self.riverActions.append(currentAction)
    
    def dealBoard(self, cards, type, second=False):
        if not second:
            if type == 'flop':
                self.flop = cards
            elif type == 'turn':
                self.turn = cards
            elif type == 'river':
                self.river = cards
            else:
                raise TypeError(f'Unrecognized board deal type {type}')
        else:
            if type == 'flop':
                self.secondFlop = cards
            elif type == 'turn':
                self.secondTurn = cards
            elif type == 'river':
                self.secondRiver = cards
            else:
                raise TypeError(f'Unrecognized board deal type {type}')

    def addWinner(self, player, amount, type=None, combination=None):
        self.winners.append(player)
        self.winningAmounts.append(amount)
        if type is not None:
            self.winningType.append(type)
        if combination is not None:
            self.winningCombination.append(combination)


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
            matches = re.search(r'"(.*)" participation with a stack of (\d+).', desc)
            player = matches.group(1)
            chips = int(matches.group(2))
            game.addApprovedPlayer(player, chips)
        elif "quits" in desc:
            matches = re.search(r'"(.*)" quits the game with a stack of (\d+).', desc)
            player = matches.group(1)
            chips = int(matches.group(2))
            game.leavesGame(player, chips)
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

        elif desc.startswith("Flop"):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            cards = cardsString[1:-1].split(', ')
            second = "(second run)" in desc
            game.currentHand.dealBoard(cards, 'flop', second)
        elif desc.startswith("Turn"):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            second = "(second run)" in desc
            game.currentHand.dealBoard(cardsString[1:-1], 'turn', second)
        elif desc.startswith("River"):
            cardsString = re.search(r'\[.*\]', desc).group(0)
            second = "(second run)" in desc
            game.currentHand.dealBoard(cardsString[1:-1], 'river', second)

        elif "shows a" in desc:
            player = desc.split('"')[1]
            cardString = re.search(r'shows a ([^.]*).', desc).group(1)
            cards = cardString.split(', ')
            game.currentHand.holeCards[player] = cards
        elif "Your hand is " in desc:
            cardString = re.search(r'Your hand is (.*)', desc).group(1)
            cards = cardString.split(', ')
            game.currentHand.holeCards[user] = cards

        elif re.search(r'collected \d+ from pot with', desc):
            matches = re.search(r'"(.*)" collected (\d+) from pot with (.+) \(combination: (.*)\)', desc)
            winner = matches.group(1)
            amount = matches.group(2)
            winningType = matches.group(3)
            combination = matches.group(4)
            game.currentHand.addWinner(winner, amount, winningType, combination)
        elif "collected" in desc:
            matches = re.search(r'"(.*)" collected (\d+) from pot', desc)
            winner = matches.group(1)
            amount = matches.group(2)
            game.currentHand.addWinner(winner, amount)
        elif "uncalled bet" in desc:
            pass

    game.endHand()
    # clean up remaining stacks and make them buyouts?
    return game
    
def compute_stats(game):
    playerStats = {player: PreflopStats(player) for player in game.playerInfo}
    for hand in game.hands:
        processedPlayers = defaultdict(int)
        counter = 1
        firstToAct=True
        smallBlindPlayer = None
        bigBlindPlayer = None
        straddlePlayer = None
        for action in hand.preflopActions:
            if action.action in ['smallBlind', 'bigBlind', 'straddle', 'missingSmallBlind', 'missingBigBlind', 'check']:
                if action.action == 'smallBlind':
                    smallBlindPlayer = action.player
                if action.action == 'bigBlind':
                    bigBlindPlayer = action.player
                if action.action == 'straddle':
                    straddlePlayer = action.player
                continue

            if firstToAct:
                playerStats[action.player].raiseFirstChances += 1
            if action.player not in processedPlayers:
                playerStats[action.player].numPlayed += 1
            
            if action.action == 'fold':   
                pass
            elif action.action in ['call', 'callAllIn']:
                if action.player not in processedPlayers:
                    playerStats[action.player].preflopCalls += 1
                    playerStats[action.player].numVoluntary += 1
                firstToAct = False
            elif action.action in ['raise', 'raiseAllIn']:
                if action.player not in processedPlayers:
                    playerStats[action.player].preflopRaises += 1
                    playerStats[action.player].numVoluntary += 1
                else:
                    playerStats[action.player].preflopReRaises += 1
                if firstToAct:
                    playerStats[action.player].raiseFirst += 1
                    firstToAct = False
                counter += 1
                if counter == 3:
                    playerStats[action.player].threeBet += 1
                elif counter == 4:
                    playerStats[action.player].fourBet += 1
                elif counter == 5:
                    playerStats[action.player].fiveBet += 1
                elif counter >= 6:
                    playerStats[action.player].sixAboveBet += 1
            else:
                print(action)
                raise TypeError("Illegal preflop move!")

            processedPlayers[action.player] += 1
        
        if firstToAct:
            if straddlePlayer is not None:
                playerStats[straddlePlayer].numPlayed += 1
            elif bigBlindPlayer is not None:
                playerStats[bigBlindPlayer].numPlayed += 1
            else:
                raise ValueError("Everyone folds, missing player!")

    return playerStats


class PreflopStats:
    def __init__(self, player) -> None:
        self.player = player
        self.numPlayed = 0
        self.numVoluntary = 0

        self.raiseFirstChances = 0
        self.raiseFirst = 0

        self.preflopRaises = 0
        self.preflopReRaises = 0
        self.preflopCalls = 0
        self.threeBet = 0
        self.fourBet = 0
        self.fiveBet = 0
        self.sixAboveBet = 0

    def __str__(self) -> str:
        return f'{self.player} VPIP {self.numVoluntary}/{self.numPlayed} ({self.numVoluntary/self.numPlayed*100:.1f}%), RFI {self.raiseFirst}/{self.raiseFirstChances}, PFR {self.preflopRaises}/{self.numPlayed}, 3BET {self.threeBet}, 4BET {self.fourBet}, 5BET {self.fiveBet}, Calls: {self.preflopCalls}'


def main():
    filename = 'cur2.csv'
    user = 'how'
    game = parseLog(filename, user)
    stats = compute_stats(game)
    df = pd.DataFrame(columns=['player','VPIP','RFI','PFR','3BET','4BET','5BET','Calls'])
    for player, stat in stats.items():
        if stat.numPlayed:
            print(stat)

if __name__=="__main__":
    main()
