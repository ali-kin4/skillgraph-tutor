#!/usr/bin/env bash
set -euo pipefail

skillgraph init data/sample_syllabus.md
skillgraph add-student s1 --name "Ada"
skillgraph study s1 --concept Variables
skillgraph quiz s1 --concept Variables --correct --confidence 0.8
skillgraph plan s1 --horizon 7d
skillgraph report s1 --out reports/s1
