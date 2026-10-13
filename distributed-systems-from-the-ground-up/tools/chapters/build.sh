#!/bin/sh
# Expands every chapter source into src/.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/../.."

python3 tools/chapters/gen.py 1 tools/chapters/01.txt src/01-key-value-store-system-design.md
python3 tools/chapters/gen.py 2 tools/chapters/02.txt src/02-key-value-store-storage-node.md
python3 tools/chapters/gen.py 3 tools/chapters/03.txt src/03-key-value-store-replication.md
python3 tools/chapters/gen.py 4 tools/chapters/04.txt src/04-key-value-store-leader-election.md
python3 tools/chapters/gen.py 5 tools/chapters/05.txt src/05-key-value-store-router.md
python3 tools/chapters/gen.py 6 tools/chapters/06.txt src/06-key-value-store-group-commit.md
python3 tools/chapters/designs.py > /dev/null
python3 tools/chapters/gen.py 7 tools/chapters/07.txt src/07-rate-limiter.md
python3 tools/chapters/gen.py 8 tools/chapters/08.txt src/08-unique-id-generator.md
python3 tools/chapters/gen.py 9 tools/chapters/09.txt src/09-distributed-cache.md
python3 tools/chapters/gen.py 10 tools/chapters/10.txt src/10-distributed-lock.md
python3 tools/chapters/gen.py 11 tools/chapters/11.txt src/11-message-queue.md
python3 tools/chapters/gen.py 12 tools/chapters/12.txt src/12-job-scheduler.md
python3 tools/chapters/gen.py 13 tools/chapters/13.txt src/13-notification-service.md
python3 tools/chapters/gen.py 14 tools/chapters/14.txt src/14-url-shortener.md
python3 tools/chapters/gen.py 15 tools/chapters/15.txt src/15-news-feed.md
python3 tools/chapters/gen.py 16 tools/chapters/16.txt src/16-object-store.md
python3 tools/chapters/gen.py 17 tools/chapters/17.txt src/17-video-streaming.md
python3 tools/chapters/gen.py 18 tools/chapters/18.txt src/18-chat.md
python3 tools/chapters/gen.py 19 tools/chapters/19.txt src/19-payment-system.md
python3 tools/chapters/gen.py 20 tools/chapters/20.txt src/20-ticket-booking.md
python3 tools/chapters/gen.py 21 tools/chapters/21.txt src/21-ride-hailing.md
python3 tools/chapters/gen.py 22 tools/chapters/22.txt src/22-search-autocomplete.md
python3 tools/chapters/gen.py 23 tools/chapters/23.txt src/23-web-crawler.md
python3 tools/chapters/gen.py 24 tools/chapters/24.txt src/24-metrics-and-monitoring.md
python3 tools/chapters/gen.py 25 tools/chapters/25.txt src/25-file-sync.md
python3 tools/chapters/gen.py 26 tools/chapters/26.txt src/26-collaborative-editing.md
python3 tools/chapters/gen.py 27 tools/chapters/27.txt src/27-stock-exchange.md
python3 tools/chapters/gen.py 28 tools/chapters/28.txt src/28-click-aggregation.md
