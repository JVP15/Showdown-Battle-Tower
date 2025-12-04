import random
import math
import os
import csv
import json
import logging
from os import listdir
from os.path import isfile, join

from poke_env.player.player import Player
from poke_env.player.battle_order import BattleOrder
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.ps_client.server_configuration import ServerConfiguration
from poke_env.battle.effect import Effect
from poke_env.battle.status import Status
from poke_env.battle.move_category import MoveCategory
from poke_env.battle.field import Field
from poke_env.battle.pokemon_gender import PokemonGender
from poke_env.data.gen_data import GenData

from damage_calc_by_post import SimpleDamageCalculator
from damage_calculator_format_pokemon import DamageCalculatorFormatPokemon
from utils import UtilityFunctions
from showdown_team_parser import ShowdownTeamParser

class BattleTowerPlayer(Player):
    def __init__(self,
                 account_configuration: AccountConfiguration,
                 server_configuration: ServerConfiguration,
                 #battle_format="gen8bdsp3v3singles",
                 battle_format="gen8customgame",
                 team=None,
                 save_replays=False,
                 log_level=logging.INFO):
        super().__init__(
            account_configuration=account_configuration,
            server_configuration=server_configuration,
            battle_format=battle_format,
            team=team,
            save_replays=save_replays,
            log_level=log_level
        )
        self.gen_data = GenData.from_gen(8)
        self.moves = self.gen_data.moves
        self.pokedex = self.gen_data.pokedex
        self.utility_functions = UtilityFunctions()
        self.active_pokemon_turn_counter = 0
        self.team_directory = {}
        self.opponent_team_directory = {}

    def choose_move(self, battle) -> BattleOrder:
        if Effect.PERISH1 in battle.active_pokemon.effects:
            if battle.available_switches:
                self.logger.debug("Found perish1, switching")
                return self.create_order(random.choice(battle.available_switches))

        top_priority_moves = [] # preferred moves are the tactical chefs' kiss. If
                             # any moves are in this list after assessing options,
                             # one of them will be chosen.
        status_moves = [] # Any status category moves (moves that don't deal damage)
        high_priority_moves = [] # Moves like Attract, Will-O-Wisp, etc.
        sleepables = []

        damage_calculator = SimpleDamageCalculator()
        if battle.available_moves:
            self.logger.debug("Available moves: %s", battle.available_moves)
            active_pokemon_stats = self.team_directory.get(self.pokemon_species(battle.active_pokemon.species))
            if active_pokemon_stats is None:
                 # Fallback if not in directory (e.g. random battle or testing)
                 active_pokemon_stats = DamageCalculatorFormatPokemon(battle.active_pokemon).formatted()

            opponent_active_pokemon_stats = DamageCalculatorFormatPokemon(battle.opponent_active_pokemon).formatted()

            self.logger.debug("Checking if opponent_team_directory is populated...")
            if len(self.opponent_team_directory.keys()) > 0:
                self.logger.debug("It is: %s", self.opponent_team_directory)
                # Use challenger's team stats to help with damage calculation.
                opponent_active_pokemon_stats = self.opponent_team_directory.get(self.pokemon_species(battle.opponent_active_pokemon.species), opponent_active_pokemon_stats)

                # The AI knows everything about the opposing Pokemon... unless its
                # species has more than one ability to choose from. Get or guess that
                # here.
                opponent_active_pokemon_stats["ability"] = self.utility_functions.get_or_guess_ability(battle.opponent_active_pokemon)

            best_move = None
            best_damage = 0
            available_moves = battle.available_moves

            if battle.active_pokemon.status == Status.SLP:
                for move in battle.available_moves:
                    if not move.sleep_usable:
                        continue

                    if move.current_pp == 0:
                        continue

                    sleepables.append(move)

            if len(sleepables) > 0:
                available_moves = sleepables

            self.logger.debug("Iterating over possible moves, which are currently: %s", available_moves)
            for move in available_moves:
                self.logger.debug("Evaluating %s...", move.id)
                if move.current_pp == 0:
                    # Skip if out of PP.
                    self.logger.debug("Out of PP.")
                    continue

                if move.id not in self.moves.keys():
                    # Might be a forced "move" like recharging after a Hyper Beam
                    self.logger.debug("Couldn't find move in dict.")
                    continue

                # Special handling for status moves.
                if move.category == MoveCategory.STATUS:
                    # If it's a move we can use, add it to status moves list.
                    self.logger.debug("It's a status move...")
                    
                    if Effect.TAUNT in battle.active_pokemon.effects:
                        # Can't use status moves while taunted.
                        self.logger.debug("Taunted, can't use.")
                        continue

                    if self.utility_functions.move_heals_user(move) and self.utility_functions.move_does_no_damage(move):
                        # Heal logic is handled elsewhere.
                        self.logger.debug("Healing move, handle elsewhere.")
                        continue

                    if move.target != "self" and not self.move_works_against_target(move, battle.active_pokemon, battle.opponent_active_pokemon):
                        # Skip if move targets a foe but foe is immune to it.
                        self.logger.debug("Foe immune to move.")
                        continue
                    elif move.target == "self" and not self.move_works_against_target(move, battle.active_pokemon, battle.active_pokemon):
                        # Skip if we can't use move on ourself (e.g. Substitute while Substitute is active)
                        self.logger.debug("Can't use this move on ourselves for some reason.")
                        continue

                    if move.weather != None and move.weather in battle.weather.keys():
                        # Don't use weather move if weather for move already active.
                        self.logger.debug("Weather already active.")
                        continue

                    if move.pseudo_weather != None and self.is_id_in_enum_dict(move.pseudo_weather, battle.fields):
                        # E.g. don't use Trick Room when it's already up.
                        self.logger.debug("pseudo_weather already active.")
                        continue

                    if move.side_condition != None and self.is_id_in_enum_dict(
                        move.side_condition, battle.side_conditions):
                        # E.g. don't use light screen when it's already up.
                        self.logger.debug("Side condition already active.")
                        continue

                    # TODO: Check slot condition (e.g. Wish)

                    if self.utility_functions.move_buffs_user(battle.active_pokemon, move) and self.utility_functions.move_boosts_are_useless(battle.active_pokemon, move):
                        # This move boosts stats, but all of the stats it boosts
                        # are already at maximum boost level.
                        self.logger.debug("Move boosts stats, but all stats it boosts are already maxed. Skipping.")
                        continue

                    if self.utility_functions.move_drops_target_speed(move) and self.is_target_faster_than_user(battle.opponent_active_pokemon, battle.active_pokemon) and self.get_boost_for_stat(battle.opponent_active_pokemon.boosts, "spe") > -6:
                        # This move drops the opponent's speed, they're faster than us, AND they're not
                        # at minimum speed yet.
                        self.logger.debug("It controls speed, opponent is faster, and opponent isn't at min speed. Adding to high priority moves.")
                        high_priority_moves.append(move)
                        continue

                    if self.utility_functions.is_useable_setup_move(battle.active_pokemon, move) and self.is_user_able_to_survive_turn(battle.active_pokemon, active_pokemon_stats, opponent_active_pokemon_stats):
                        # If we have a setup move, and our opponent can't KO us this turn,
                        # add to high priorities.
                        high_priority_moves.append(move)
                        continue

                    if move.status != None or move.volatile_status != None:
                        self.logger.debug("It inflicts either a primary or secondary status.")
                        if self.is_high_priority_status_move(move, battle.active_pokemon, battle.opponent_active_pokemon):
                            self.logger.debug("Status is high priority. Adding to high priority moves.")
                            high_priority_moves.append(move)
                            continue

                    if move.id == "reflect":
                        high_priority_moves.append(move)
                        continue

                    self.logger.debug("Normal, viable status move. Adding to status move list.")
                    status_moves.append(move)
                    continue

                if move.id == "fakeout" and self.active_pokemon_turn_counter > 1:
                    # Fake Out only works on the first turn, so skip.
                    self.logger.debug("It's fake out. Skipping due to turn counter.")
                    continue
                elif move.id == "fakeout":
                    # Now a high priority move.
                    high_priority_moves.append(move)
                    continue

                if move.heal > 0 and battle.active_pokemon.current_hp_fraction == 1:
                    self.logger.debug("Healing move, but we're max HP. Skipping.")
                    continue

                if move.id == "dreameater" and battle.opponent_active_pokemon.status != Status.SLP:
                    # Dream eater only works on sleeping targets.
                    continue

                move_data = self.moves[move.id]
                if "ohko" in move_data.keys() and move_data.get("ohko") and self.move_works_against_target(move, battle.active_pokemon, battle.opponent_active_pokemon):
                    # Treat OHKO moves as status moves priority; i.e.,
                    # equal chance to come out as best move, other status moves,
                    # but not favoured over high priority moves and staying
                    # alive.
                    status_moves.append(move)
                    continue
                if "damageCallback" in move_data.keys():
                    # Moves like counter, metal burst, mirror coat, and endeavor.
                    # Treat as status moves.
                    status_moves.append(move)

                self.logger.debug("Simulating damage roll for %s", move.id)
                move_name = self.moves[move.id].get("name", None)
                self.logger.debug("Simulating damage for %s", move_name)
                simulated_damage = 0

                # Check for calculated or fixed damage.
                if move.damage == "level":
                    simulated_damage = battle.opponent_active_pokemon.level
                elif move.damage > 0:
                    simulated_damage = move.damage
                else:
                    num_hits = random.randint(move.n_hit[0], move.n_hit[1])
                    simulated_damage = 0
                    hit_count = 0

                    while hit_count < num_hits:
                        simulated_damage = simulated_damage + damage_calculator.calculate(active_pokemon_stats, opponent_active_pokemon_stats, move_name)
                        hit_count = hit_count + 1

                self.logger.debug("Damage simulated was %s", simulated_damage)

                if simulated_damage >= self.guess_current_hp(battle.opponent_active_pokemon):
                    # Does this move knock out our opponent? If so, add to preferred moves.
                    self.logger.info("Potential KO; adding to top priority moves.")
                    top_priority_moves.append(move)
                    continue

                if self.utility_functions.move_drops_target_speed(move) and self.is_target_faster_than_user(battle.opponent_active_pokemon, battle.active_pokemon) and self.get_boost_for_stat(battle.opponent_active_pokemon.boosts, "spe") > -6:
                    if self.move_works_against_target(move, battle.active_pokemon, battle.opponent_active_pokemon):
                        # Speed control is second only to potential KOs.
                        self.logger.debug("Judged target to be faster than us, and %s seems to lower speed. Adding to high priority moves.", move.id)
                        high_priority_moves.append(move)
                        continue

                if simulated_damage > best_damage:
                    self.logger.debug("Which is greater than current best, which was %s, updating best move to %s", best_damage, move_name)
                    best_damage = simulated_damage
                    best_move = move

            if len(top_priority_moves) > 0:
                self.logger.debug("Selecting a potential KO move from %s top priority moves: %s", len(top_priority_moves), top_priority_moves)
                self.logger.debug("Checking for moves with priority...")
                priority_ko_moves = []
                
                for ko_move in top_priority_moves:
                    if ko_move.priority > 0:
                        priority_ko_moves.append(ko_move)

                if len(priority_ko_moves) > 0:
                    return self.create_order(random.choice(priority_ko_moves))
                
                return self.create_order(random.choice(top_priority_moves))

            # We don't see any potential KOs at present, so combine best damage move
            # with status moves into a single pool and set that as our current
            # best move.
            move_options = status_moves
            highest_damage_move = best_move

            if best_move is not None:
                move_options.append(best_move)
            
            self.logger.debug("Normal move options at this point are %s", move_options)

            if len(move_options) > 0:
                best_move = random.choice(move_options)

            if len(high_priority_moves) > 0:
                self.logger.debug("1 or more high priority moves found: %s", high_priority_moves)
                if highest_damage_move is not None:
                    self.logger.debug("Adding %s to options, as it's our highest damage move.", highest_damage_move.id)
                    high_priority_moves.append(highest_damage_move)
                self.logger.debug("Selecting one.")
                return self.create_order(random.choice(high_priority_moves))

            if best_move is None:
                self.logger.info("No good moves! Trying to switch...")
                if len(battle.available_switches) > 0:
                    self.active_pokemon_turn_counter = 0
                    return self.create_order(self.make_smart_switch(
                    battle.opponent_active_pokemon, battle.available_switches))

                self.logger.info("No switches available! Choose random move.")
                return self.choose_random_move(battle)

            return self.create_order(best_move)
        elif len(battle.available_switches) > 0:
            self.active_pokemon_turn_counter = 0
            return self.create_order(self.make_smart_switch(
                battle.opponent_active_pokemon, battle.available_switches))
        else:
            # Random switch.
            self.active_pokemon_turn_counter = 0
            return self.choose_random_move(battle)

    def make_smart_switch(self, opponent_pokemon, available_switches):
        if len(available_switches) == 1:
            # It may not be the smart choice, but it's our only choice.
            return available_switches[0]

        good_switch_ins = []
        for switch_option in available_switches:
            for move in switch_option.moves.values():
                if opponent_pokemon.damage_multiplier(move) > 1:
                    # This Pokemon has a super effective move against the
                    # opponent. Add to our good switch-in list.
                    good_switch_ins.append(switch_option)

        if len(good_switch_ins) > 0:
            # We have at least one good switch-in! Choose one at random.
            return random.choice(good_switch_ins)

        # Otherwise... choose anything. It's all the same.
        return random.choice(available_switches)

    def teampreview(self, battle):
        # Try to cache opponent's team's stats for damage calculation.
        opponent_team_path = ".\\config\\Challenger Teams"
        self.logger.info("Attempting to find opponent's team on disk...")
        if os.path.exists(opponent_team_path):
            self.logger.info("Team path found...")
            showdown_team_parser = ShowdownTeamParser()
            self.logger.debug("Gathering file names...")
            team_files = [f for f in listdir(opponent_team_path) if isfile(join(opponent_team_path, f))]
            self.logger.debug("%s found: %s", len(team_files), team_files)

            for team_file in team_files:
                self.logger.debug("Reading %s...", team_file)
                lines = []
                team = ""
                with open(opponent_team_path + "\\" + team_file) as f:
                    #lines = f.readlines()
                    team = f.read()
                
                self.logger.debug("Parsing team...")
                team_dir = showdown_team_parser.parse_team(team)
                find_count = 0

                self.logger.debug("Iterating over opponent's team in preview...")
                for opponent_pokemon in battle.opponent_team.values():
                    self.logger.debug("Checking pokemon species in team dir's keys...")
                    self.logger.debug("Opponent pokemon species is: %s", self.pokemon_species(opponent_pokemon.species))
                    self.logger.debug("Team dir's keys are: %s", team_dir.keys())
                    if self.pokemon_species(opponent_pokemon.species) in team_dir.keys():
                        self.logger.debug("Pokemon found! Incrementing find count to %s", find_count)
                        find_count = find_count + 1
                    else:
                        self.logger.debug("No match. Wrong file.")
                        break

                self.logger.debug("Checking find count (it's %s)", find_count)
                if find_count == len(battle.opponent_team.values()):
                    self.logger.info("They're all here! Update opponent_team_directory.")
                    # Found the whole team in this showdown file.
                    self.opponent_team_directory = team_dir
                    self.logger.debug("opponent_team_directory is: %s", self.opponent_team_directory)
                    break

        return "/team 123"

    def pokemon_species(self, species_id):
        if species_id not in self.pokedex.keys():
            return species_id

        return self.pokedex[species_id].get('name')

    def guess_current_hp(self, pokemon):
        self.logger.debug("Guessing %s's current HP.", pokemon.species)
        max_hp = self.guess_max_hp(pokemon)
        self.logger.debug("Max HP (guess): %s", max_hp)
        current_hp =  (pokemon.current_hp_fraction) * max_hp
        self.logger.debug("Current HP (guess): %s", current_hp)
        return current_hp

    def guess_max_hp(self, pokemon):
        pokedex_entry = self.pokedex[pokemon.species];
        hp_base = pokedex_entry.get('baseStats').get('hp')
        iv = 31
        ev = 0

        if pokedex_entry.get('name') in self.opponent_team_directory.keys():
            # We have the exact stats for this one. Use those instead.
            directory_pokemon = self.opponent_team_directory[pokedex_entry.get('name')]
            
            ev = self.utility_functions.get_ev_from_stat_block(directory_pokemon, "hp")
            iv = self.utility_functions.get_iv_from_stat_block(directory_pokemon, "hp")

        return math.floor(0.01 * (2 * hp_base + iv + math.floor(0.25 * ev)) * pokemon.level) + pokemon.level + 10

    def move_works_against_target(self, move, user, target):
        move_data = self.moves[move.id]

        if move.status is not None and target.status is not None:
            # Pokemon can only have one major status ailment at a time.
            return False

        if move.volatile_status is not None:
            # E.g. confusion, taunted, leech seed -- can't have same one twice.
            target_effects = list(target.effects.keys())
            for effect in target_effects:
                if self.id_from_enum_value(effect) == move.volatile_status:
                    return False
                
            if move.volatile_status == "followme":
                # Singles only, so follow me won't work either.
                return False

            if move.volatile_status == "encore" and target.first_turn:
                # Don't try to encore when they haven't performed yet.
                return False

            if move.volatile_status == "yawn" and target.status is not None:
                # Yawn doesn't work if the opponent can't sleep.
                return False

            if move.volatile_status == "stockpile" and Effect.STOCKPILE3 in user.effects:
                # Can't stockpile more than 3 times.
                return False

        if not (target.damage_multiplier(move) > 0):
            # Move doesn't work due to typing.
            return False

        self.logger.debug("Checking abilities...")
        if self.utility_functions.is_move_negated_by_ability(move,
            self.utility_functions.get_or_guess_ability(user),
            self.utility_functions.get_or_guess_ability(target)):
            return False

        # TODO: Check item.

        if move.volatile_status == "attract" and not self.genders_are_attract_compatible(user.gender, target.gender):
            return False

        if "sleepUsable" in move_data.keys() and move_data.get("sleepUsable") and user.status != Status.SLP:
            # Can't use sleep usable move if we're not asleep.
            return False

        if "sleepUsable" not in move_data.keys() and user.status == Status.SLP:
            # Conversely, can't use non-sleep usable moves when we ARE asleep.
            return False

        if move.target != "self" and Effect.SUBSTITUTE in list(target.effects.keys()):
            if move.category == MoveCategory.STATUS and self.utility_functions.move_targets_single_pokemon(move.target):
                # Status moves don't work on substitutes of other Pokemon.
                return False

        return True

    def genders_are_attract_compatible(self, gender1, gender2):
        if gender1 == PokemonGender.MALE:
            return gender2 == PokemonGender.FEMALE

        if gender1 == PokemonGender.FEMALE:
            return gender2 == PokemonGender.MALE

        return False

    def is_id_in_enum_dict(self, id_text, enum_dict):
        for enum_value in enum_dict.keys():
            if id_text == self.id_from_enum_value(enum_value):
                return True

        return False

    def id_from_enum_value(self, enum_value):
        enum_value_text = enum_value.name
        enum_value_text = enum_value_text.lower()
        return enum_value_text.replace("_", "")

    def is_high_priority_status_move(self, move, user, target):
        if move.status != None:
            # All primary status is good.
            return True

        if move.volatile_status == "attract":
            return True

        if move.volatile_status == "confusion":
            return True

        if move.volatile_status == "partiallyTrapped":
            return True

        return False

    def is_target_faster_than_user(self, target, user):
        target_speed_nom_and_dom = [2, 2]
        if target.boosts != None and "spe" in target.boosts.keys():
            target_speed_nom_and_dom = self.utility_functions.calculate_stat_fraction(target.boosts["spe"])

        user_speed_nom_and_dom = [2, 2]
        if user.boosts != None and "spe" in user.boosts.keys():
            user_speed_nom_and_dom = self.utility_functions.calculate_stat_fraction(user.boosts["spe"])

        target_speed_factor = target_speed_nom_and_dom[0] / target_speed_nom_and_dom[1]
        user_speed_factor = user_speed_nom_and_dom[0] / user_speed_nom_and_dom[1]

        target_base_speed = self.calculate_speed_stat(target, False)
        user_base_speed = self.calculate_speed_stat(user, True)

        target_actual_speed = math.floor(target_base_speed * target_speed_factor)
        self.logger.debug("Calculated target's actual speed at %s", target_actual_speed)

        user_actual_speed = math.floor(user_base_speed * user_speed_factor)
        self.logger.debug("Calculated user's actual speed at %s", user_actual_speed)

        return target_actual_speed > user_actual_speed

    def calculate_speed_stat(self, pokemon, is_own):
        stat_block = {}
        pokemon_name = self.pokemon_species(pokemon.species)

        if is_own:
            stat_block = self.team_directory.get(self.pokemon_species(pokemon.species))
        else:
            stat_block = self.opponent_team_directory.get(self.pokemon_species(pokemon.species))
        
        if stat_block is None:
             # Fallback
             return self.pokedex[pokemon.species].get("baseStats").get("spe")

        base_speed = self.pokedex[pokemon.species].get("baseStats").get("spe")
        iv = self.utility_functions.get_iv_from_stat_block(stat_block, "spe")
        ev = self.utility_functions.get_ev_from_stat_block(stat_block, "spe")

        nature_mod = self.utility_functions.get_mod_for_nature(stat_block.get("nature"), "spe")

        result = (math.floor(0.01 * (2 * base_speed + iv + math.floor(0.25 * ev)) * pokemon.level) + 5) * nature_mod
        self.logger.debug("Calculated %s's unmodified speed at %s", pokemon_name, int(result))
        return result

    def get_boost_for_stat(self, boosts, stat):
        self.logger.debug("Getting %s boost level.", stat)
        if boosts is None:
            return 0

        if stat not in boosts.keys():
            return 0

        self.logger.debug("Found boost. It's %s", boosts[stat])
        return boosts[stat]

    def is_user_able_to_survive_turn(self, active_pokemon, active_pokemon_stats, opponent_active_pokemon_stats):
        damage_calculator = SimpleDamageCalculator()

        for move in opponent_active_pokemon_stats["moves"]:
            # Holy crap we're actually using the moves from the stat block.
            simulated_damage = damage_calculator.calculate(opponent_active_pokemon_stats, active_pokemon_stats, move)

            if simulated_damage >= active_pokemon.current_hp:
                # Move could knock us out. RIP.
                return False

        return True