import sys
import importlib
import argparse
import time
import os
import numpy as np

from game import Game
from players.guesser import *
from players.codemaster import *

class GameRun:
    """Class that builds and runs a Game based on command line arguments"""

    def __init__(self):
        parser = argparse.ArgumentParser(
            description="Run the Codenames AI competition game.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("codemaster", help="import string of form A.B.C.MyClass or 'human'")
        parser.add_argument("guesser", help="import string of form A.B.C.MyClass or 'human'")
        parser.add_argument("--seed", help="Random seed value for board state -- integer or 'time'", default='time')

        parser.add_argument("--w2v", help="Path to w2v file or None", default=None)
        parser.add_argument("--glove", help="Path to glove file or None", default=None)
        parser.add_argument("--wordnet", help="Name of wordnet file or None, most like ic-brown.dat", default=None)
        parser.add_argument("--glove_cm", help="Path to glove file or None", default=None)
        parser.add_argument("--glove_guesser", help="Path to glove file or None", default=None)
        parser.add_argument("--bert_cm", help="Path to bert file or None", default=None)
        parser.add_argument("--bert_guesser", help="Path to bert file or None", default=None)
        parser.add_argument("--num_cluewords", help="Number of words in clue pool", default=None)
        parser.add_argument("--num_gamewords", help="Number of words in game pool", default=None)

        parser.add_argument("--no_log", help="Supress logging", action='store_true', default=False)
        parser.add_argument("--no_print", help="Supress printing", action='store_true', default=False)
        parser.add_argument("--game_name", help="Name of game in log", default="default")
        parser.add_argument("--train", help="Train over n games", default = False)
        parser.add_argument("--test", help= "Test Q matrix over n games", default = False)
        parser.add_argument("--q_file", help=".matrix file for learned Q matrix", default=None)

        args = parser.parse_args()

        self.do_log = not args.no_log
        self.do_print = not args.no_print
        if not self.do_print:
            self._save_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
        self.game_name = args.game_name

        self.g_kwargs = {}
        self.cm_kwargs = {}
        self.num_cluewords = args.num_cluewords



        self.num_gamewords = None if args.num_gamewords is None else int(args.num_gamewords)
        self.train = args.train
        self.test = args.test

        # load codemaster class
        if args.codemaster == "human":
            self.codemaster = HumanCodemaster
            print('human codemaster')
            assert(args.num_cluewords is None)
        else:
            self.codemaster = self.import_string_to_class(args.codemaster)
            print('loaded codemaster class')
            #cluewords should be >> 100, we run out of clues for long games and crash
            self.cm_kwargs["wordlist_len"] = None if args.num_cluewords is None else int(args.num_cluewords)

        # load guesser class
        if args.guesser == "human":
            self.guesser = HumanGuesser
            print('human guesser')
        else:
            self.guesser = self.import_string_to_class(args.guesser)
            print('loaded guesser class')

        # if the game is going to have an ai, load up word vectors
        if sys.argv[1] != "human" or sys.argv[2] != "human":
            if args.wordnet is not None:
                brown_ic = Game.load_wordnet(args.wordnet)
                if sys.argv[1] != "human":
                    self.cm_kwargs["brown_ic"] = brown_ic
                if sys.argv[2] != "human":
                    self.g_kwargs["brown_ic"] = brown_ic
                print('loaded wordnet')

            if args.glove is not None:
                glove_vectors = Game.load_glove_vecs(args.glove)
                if sys.argv[1] != "human":
                    self.cm_kwargs["glove_vecs"] = glove_vectors
                if sys.argv[2] != "human":
                    self.g_kwargs["glove_vecs"] = glove_vectors
                print('loaded glove vectors')

            if args.w2v is not None:
                w2v_vectors = Game.load_w2v(args.w2v)
                if sys.argv[1] != "human":
                    self.cm_kwargs["word_vectors"] = w2v_vectors
                if sys.argv[2] != "human":
                    self.g_kwargs["word_vectors"] = w2v_vectors
                print('loaded word vectors')

            if args.glove_cm is not None:
                assert(sys.argv[1] != "human")
                glove_vectors = Game.load_glove_vecs(args.glove_cm)
                self.cm_kwargs["glove_vecs"] = glove_vectors
                print('loaded glove vectors')

            if args.glove_guesser is not None:
                assert(sys.argv[2] != "human")
                glove_vectors = Game.load_glove_vecs(args.glove_guesser)
                self.g_kwargs["glove_vecs"] = glove_vectors
                print('loaded glove vectors')

            if args.bert_cm is not None:
                assert(sys.argv[1] != "human")
                bert_vectors = Game.load_glove_vecs(args.bert_cm)
                self.cm_kwargs["bert_vecs"] = bert_vectors
                print('loaded BERT vectors')

            if args.bert_guesser is not None:
                assert(sys.argv[2] != "human")
                bert_vectors = Game.load_glove_vecs(args.bert_guesser)
                self.g_kwargs["bert_vecs"] = bert_vectors
                print('loaded BERT vectors')

            if args.q_file is not None:
                assert(sys.argv[2] != "human")
                self.g_kwargs["Q_file"] = args.q_file
                print("loaded Q file")




        # set seed so that board/keygrid can be reloaded later
        if args.seed == 'time':
            self.seed = time.time()
        else:
            self.seed = int(args.seed)

    def __del__(self):
        """reset stdout if using the do_print==False option"""
        if not self.do_print:
            sys.stdout.close()
            sys.stdout = self._save_stdout

    def import_string_to_class(self, import_string):
        """Parse an import string and return the class"""
        parts = import_string.split('.')
        module_name = '.'.join(parts[:len(parts) - 1])
        class_name = parts[-1]

        module = importlib.import_module(module_name)
        my_class = getattr(module, class_name)

        return my_class


if __name__ == "__main__":
    game_setup = GameRun()

    game = Game(game_setup.codemaster,
                game_setup.guesser,
                seed=game_setup.seed,
                do_print=game_setup.do_print,
                do_log=game_setup.do_log,
                game_name=game_setup.game_name,
                cm_kwargs=game_setup.cm_kwargs,
                g_kwargs=game_setup.g_kwargs,
                num_words = game_setup.num_gamewords,
                train=game_setup.train,
                test = game_setup.test)
    
    

    if game_setup.train:
        num_games = 100
        Q = game.learnQ(num_games)
        Q_filename = "Q_" + str(game_setup.num_gamewords) + "_" + str(game_setup.num_cluewords) + ".matrix"
        with open(Q_filename, 'wb') as file:
            np.save(file, Q)
    elif game_setup.test:
        num_games = 100
        game.testQ(num_games)
    else:
        game.run()
