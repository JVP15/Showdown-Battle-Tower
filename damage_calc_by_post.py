import subprocess
import json
import os
import random

class SimpleDamageCalculator():
    # Expected format:
    #    attackerObject = {
    #    "species": "Serperior", //species name AS IT IS IN THE POKEDEX  [REQUIRED]
    #    "ability": "Contrary", //ability [REQUIRED]
    #    "item": "Leftovers",  //item [REQUIRED]
    #    "level": 100, //level [REQUIRED], must be a number
    #    "nature": "Modest", //not required, defaults to serious
    #    "evs": {"spa": 252, "spe": 252},  //not required, defaults to 0 in all stats. Valid stats are "hp", "atk", "spa", "def", "spd", "spe"
    #    "ivs": {"atk": 0} //not required, defaults to 31 in any stat not specified
    #}
    def calculate(self, attacker, defender, move):
        #attackerObject = {
        #    "species": attacker.species, #species name AS IT IS IN THE POKEDEX  [REQUIRED]
        #    "ability": attacker.ability, #ability [REQUIRED]
        #    "item": attacker.item,  #item [REQUIRED]
        #    "level": 50, #level [REQUIRED], must be a number
        #}

        #defenderObject = {
        #    "species": defender.species, #species name AS IT IS IN THE POKEDEX  [REQUIRED]
        #    "ability": defender.ability, #ability [REQUIRED]
        #    "item": defender.item,  #item [REQUIRED]
        #    "level": 50, #level [REQUIRED], must be a number
        #}

        print(attacker)
        print(defender)
        
        payload = { 'attacker': attacker, 'defender': defender, 'move': move }
        
        # Path to bridge.js
        bridge_path = os.path.join(os.path.dirname(__file__), 'bridge.js')
        
        try:
            process = subprocess.Popen(
                ['node', bridge_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate(input=json.dumps(payload))
            
            if stderr:
                print("Error from bridge.js:")
                print(stderr)
            
            if not stdout:
                print("No output from bridge.js")
                return 0
                
            jsonResult = json.loads(stdout)
            # print(jsonResult) # Debugging

            if 'error' in jsonResult:
                # Something went wrong. Print error and return 0.
                print (jsonResult['error'])
                return 0

            if 'damage' in jsonResult:
                damage_values = jsonResult['damage']
                if isinstance(damage_values, list) and len(damage_values) > 0:
                     return random.choice(damage_values)
                elif isinstance(damage_values, (int, float)):
                    return damage_values
            
            return 0
            
        except Exception as e:
            print(f"Exception during damage calculation: {e}")
            return 0

    def check_for_error(self, attacker, defender, move):
        # Re-implement check_for_error using the same bridge logic
        payload = { 'attacker': attacker, 'defender': defender, 'move': move }
        bridge_path = os.path.join(os.path.dirname(__file__), 'bridge.js')
        
        try:
            process = subprocess.Popen(
                ['node', bridge_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate(input=json.dumps(payload))
            
            if stderr:
                return f"Bridge Error: {stderr}"
                
            jsonResult = json.loads(stdout)

            if 'error' in jsonResult:
                return jsonResult['error']

            return "OK"
        except Exception as e:
            return f"Exception: {e}"