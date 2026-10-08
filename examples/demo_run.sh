#!/usr/bin/env bash
set -euo pipefail

skillgraph init data/sample_syllabus.md
skillgraph add-student s1 --name "Ada"
skillgraph study s1 Variables
skillgraph quiz s1 Variables --correct --confidence 0.8
skillgraph quiz s1 Variables --no-correct --confidence 0.6
skillgraph review s1
skillgraph plan s1 --horizon 7d
skillgraph report s1 --out reports/s1
