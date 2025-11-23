import random
import csv
from os import listdir
from os.path import isfile, join
from showdown_team_parser import ShowdownTeamParser
from poke_env.battle.pokemon import Pokemon
from poke_env.battle.move import Move

class ShowdownTeamProvider:
    def __init__(self):
        # Build trainer set directory
        self.trainer_set_directory = {}
        self.trainer_names = {}
        csv_path = ".\\Trainer CSVs"
        trainer_files = [f for f in listdir(csv_path) if isfile(join(csv_path, f))]

        for trainer_file in trainer_files:
            csv_file = open(csv_path + "\\" + trainer_file)
            csv_reader = csv.reader(csv_file)
            name_and_set_data = []
            name_and_set_data = next(csv_reader)
            full_name = name_and_set_data[0]
            short_name = name_and_set_data[1]
            self.trainer_names[short_name] = full_name

            trainer_sets = []
            idx = 2
            while idx < len(name_and_set_data):
                set_name = name_and_set_data[idx]
                if set_name not in self.trainer_set_directory.keys():
                    self.trainer_set_directory[set_name] = []
                
                self.trainer_set_directory[set_name].append(short_name) 
                idx = idx + 1
            csv_file.close()

    def get_specific_team(self, trainer_name, team_name):
        team_file_path = join("Showdown Format Teams", trainer_name, team_name + ".txt")
        team_file = open(team_file_path)
        team = team_file.read()
        team_file.close()
        return [trainer_name, team]

    def read_teams(self, trainer_name, set_name):
        trainer_file_path = join("Trainer CSVs", trainer_name + ".csv")
        trainer_file = open(trainer_file_path)
        csv_reader = csv.reader(trainer_file)
        line = []
        line = next(csv_reader)
        teams = []
        reading_set = False

        for row in csv_reader:
            if not reading_set:
                # Find set first.
                reading_set = row[0] == set_name
                continue

            # Found set. Now collect the team names.
            if len(row) == 1 and "Team" in row[0]:
                # Team label. Add it to collection.
                teams.append(row[0])
            elif len(row) == 1:
                # New set. Bail out.
                break

        trainer_file.close()
        return teams

    def get_random_team(self, set_name: str):
        trainer_name = random.choice(self.trainer_set_directory[set_name])
        trainer_full_name = self.trainer_names[trainer_name]
        print("Randomly selected " + trainer_full_name + " from set " + set_name)
        teams = self.read_teams(trainer_name, set_name)

        # Pick a team at random and find team file.
        team = random.choice(teams)
        log = "Randomly selected " + team + " from set " + set_name
        print(log)
        
        return self.get_specific_team(trainer_name, team)

    def get_worst_matchups_in_master(self, sdn_challenger_team: str):
        print("Retrieving worst matchups in master for following team:")
        print(sdn_challenger_team)
        parser = ShowdownTeamParser()
        matchup_list = [] # To begin with, this will be a list of strings with
                          # trainer name, team number, and matchup rating.
        
        challenger_team = parser.parse_team(sdn_challenger_team)
        print("All trainers in master class:")

        for mc_trainer_name in self.trainer_set_directory["M"]:
            teams = self.read_teams(mc_trainer_name, "M")

            for mc_team_number in teams:
                sdn_mc_team = self.get_specific_team(mc_trainer_name, mc_team_number)[1]
                mc_team = parser.parse_team(sdn_mc_team)

                matchup_rating = 0

                # Check each MC team pokemon's offensive and defensive capabilities
                # vs each of the challenger team's pokemon.
                for mc_pokemon in mc_team.values():
                    mc_poke_env_pokemon = Pokemon(gen=8, species=self.get_id(mc_pokemon["species"]))
                    
                    for challenger_pokemon in challenger_team.values():
                        challenger_poke_env_pokemon = Pokemon(gen=8, species=self.get_id(challenger_pokemon["species"]))

                        # Increase rating based on how good our moves are against challenger pokemon.
                        for move in mc_pokemon["moves"]:
                            mc_poke_env_move = Move(self.get_id(move), gen=8)

                            if mc_poke_env_move.base_power == 0:
                                # Ignore non-damaging moves.
                                continue

                            matchup_rating = matchup_rating + challenger_poke_env_pokemon.damage_multiplier(mc_poke_env_move)

                        # Decrease based on how good challenger pokemon's moves are against us.
                        for move in challenger_pokemon["moves"]:
                            challenger_poke_env_move = Move(self.get_id(move), gen=8)

                            if challenger_poke_env_move.base_power == 0:
                                # Ignore non-damaging moves.
                                continue

                            matchup_rating = matchup_rating - mc_poke_env_pokemon.damage_multiplier(challenger_poke_env_move)

                report = [mc_trainer_name, mc_team_number, matchup_rating]
                matchup_list.append(report)

        def matchup_rating(report):
            return report[2]

        matchup_list.sort(key=matchup_rating, reverse=True)
        result = []

        for report in matchup_list:
            result.append([report[0], report[1]])

        return result

    def get_id(self, raw_value: str):
        return raw_value.replace("-", "").replace(" ", "").replace(".", "").lower().strip()