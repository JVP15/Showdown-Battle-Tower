import subprocess
import json
import os
import random
import logging

logger = logging.getLogger(__name__)

class SimpleDamageCalculator():
    def calculate(self, attacker: dict[str, str | int], defender: dict[str, str | int], move: str):
        #attackerObject = {
        #    "species": attacker.species, #species name AS IT IS IN THE POKEDEX  [REQUIRED]
        #    "ability": attacker.ability, #ability [REQUIRED]
        #    "item": attacker.item,  #item 
        #    "level": 50, #level [REQUIRED], must be a number
        #}

        #defenderObject = {
        #    "species": defender.species, #species name AS IT IS IN THE POKEDEX  [REQUIRED]
        #    "ability": defender.ability, #ability [REQUIRED]
        #    "item": defender.item,  #item 
        #    "level": 50, #level [REQUIRED], must be a number
        #}
        # Poke env uses 'unknown_item' when the item isn't known, but that doesn't play nice with the bridge so we take it out
        attacker = attacker.copy()
        if 'item' in attacker and attacker['item'] == 'unknown_item':
            del attacker['item']
        
        defender = defender.copy()
        if 'item' in defender and defender['item'] == 'unknown_item':
            del defender['item']
        
        payload = { 'attacker': attacker, 'defender': defender, 'move': move }

        bridge_path = os.path.join(os.path.dirname(__file__), 'bridge.js')
        try:
            json_payload = json.dumps(payload)
            process = subprocess.Popen(
                ['node', bridge_path, json_payload],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate()

            if stderr:
                logger.error("Error from bridge.js: %s", stderr)
            
            if not stdout:
                logger.warning("No output from bridge.js")
                return 0
                
            jsonResult = json.loads(stdout)

            if 'error' in jsonResult:
                # Something went wrong. Print error and return 0.
                logger.error(jsonResult['error'])
                return 0

            if 'damage' in jsonResult:
                damage_values = jsonResult['damage']
                if isinstance(damage_values, list) and len(damage_values) > 0:
                     return random.choice(damage_values)
                elif isinstance(damage_values, (int, float)):
                    return damage_values
            
            return 0
            
        except Exception as e:
            logger.exception("Exception during damage calculation: %s", e)
            return 0

    def check_for_error(self, attacker, defender, move):
        # Re-implement check_for_error using the same bridge logic
        payload = { 'attacker': attacker, 'defender': defender, 'move': move }
        bridge_path = os.path.join(os.path.dirname(__file__), 'bridge.js')
        
        try:
            json_payload = json.dumps(payload)
            process = subprocess.Popen(
                ['node', bridge_path, json_payload],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate()
            
            if stderr:
                return f"Bridge Error: {stderr}"
                
            jsonResult = json.loads(stdout)

            if 'error' in jsonResult:
                return jsonResult['error']

            return "OK"
        except Exception as e:
            return f"Exception: {e}"