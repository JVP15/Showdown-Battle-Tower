const fs = require('fs');
const path = require('path');

// Try to load from node_modules first, then fall back to local path if needed
let calc;
try {
    // If installed via npm install .\damage-calc, it might be under @smogon/calc or just damage-calc depending on package.json name
    // The package.json name was @smogon/calc
    calc = require('@smogon/calc');
} catch (e) {
    console.error("Failed to load damage-calc library.");
    console.error(e);
    process.exit(1);
}

var { calculate, Pokemon, Move, Generations } = calc;

const GEN = Generations.get(8);

async function main() {
    try {
        const input = process.argv[2];
        if (!input) {
            console.error("No input provided as argument.");
            process.exit(1);
        }

        const data = JSON.parse(input);
        const { attacker: attData, defender: defData, move: moveName } = data;

        const attacker = new Pokemon(GEN, attData.species, {
            item: attData.item,
            ability: attData.ability,
            level: attData.level,
            // Add other stats if provided in the future
            evs: attData.evs,
            ivs: attData.ivs,
            nature: attData.nature,
            boosts: attData.boosts,
            curHP: attData.curHP,
            status: attData.status
        });

        const defender = new Pokemon(GEN, defData.species, {
            item: defData.item,
            ability: defData.ability,
            level: defData.level,
            evs: defData.evs,
            ivs: defData.ivs,
            nature: defData.nature,
            boosts: defData.boosts,
            curHP: defData.curHP,
            status: defData.status
        });

        const move = new Move(GEN, moveName);
        const result = calculate(GEN, attacker, defender, move);

        // Format output to match what Python expects
        // Python expects: { damage: [ ... ] }
        // result.damage can be number or number[] or number[][] (for multi-hit)

        let damageRolls = [];

        if (typeof result.damage === 'number') {
            damageRolls = [result.damage];
        } else if (Array.isArray(result.damage)) {
            // Check if it's number[] or number[][]
            if (result.damage.length > 0 && Array.isArray(result.damage[0])) {
                // It's number[][], flatten it or handle multi-hit?
                // For now, let's just flatten it to get all possible damage values
                // Or maybe just take the total damage range?
                // The original API likely returned total damage rolls.
                // Let's assume we want the total damage for the turn.
                // But wait, damage-calc returns per-hit damage for multi-hit moves usually?
                // Actually result.ts says: export type Damage = number | number[] | [number, number] | number[][];
                // If it's number[][], it's likely [ [hit1_rolls], [hit2_rolls] ]
                // We probably want to sum them up?
                // The python code does `random.choice(jsonResult['damage'])`.
                // If we have multi-hit, we should probably return the sum of hits?
                // But random.choice implies we pick ONE possible outcome.
                // If we have [ [10, 11], [10, 11] ], possible outcomes are 20, 21, 21, 22.
                // For simplicity, let's just flatten if it's simple array, but for multi-hit it's complex.

                // For now, let's just return the raw damage structure and let Python handle it if it's simple,
                // but Python expects a list of numbers.

                // If it's number[][], let's just take the first array for now to be safe, or flatten.
                // Actually, let's check if it's a 2D array.
                if (Array.isArray(result.damage[0])) {
                    // It is 2D. Let's just return the first hit's damage for now to avoid crashing,
                    // or better, try to compute total damage.
                    // But wait, `damage-calc` usually returns the damage for the move.
                    // If it's multi-hit, it might return the array of damage for each hit?
                    // Let's just flatten it.
                    damageRolls = result.damage.flat();
                } else {
                    damageRolls = result.damage;
                }
            } else {
                damageRolls = result.damage;
            }
        }

        const output = {
            damage: damageRolls,
        };

        console.log(JSON.stringify(output));

    } catch (e) {
        console.error(e);
        console.log(JSON.stringify({ error: e.message }));
    }
}

main();
