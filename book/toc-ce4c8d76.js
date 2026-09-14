// Populate the sidebar
//
// This is a script, and not included directly in the page, to control the total size of the book.
// The TOC contains an entry for each page, so if each page includes a copy of the TOC,
// the total size of the page becomes O(n**2).
class MDBookSidebarScrollbox extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        this.innerHTML = '<ol class="chapter"><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="preface.html">Preface</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="the-code.html">The code</a></span></li><li class="chapter-item expanded "><li class="part-title">Part I: Sequences and Maps</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="01-two-sum.html"><strong aria-hidden="true">1.</strong> 1. Two Sum</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="02-valid-parentheses.html"><strong aria-hidden="true">2.</strong> 2. Valid Parentheses</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="03-min-stack.html"><strong aria-hidden="true">3.</strong> 3. Min Stack</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="04-sliding-window.html"><strong aria-hidden="true">4.</strong> 4. Longest Substring Without Repeating Characters</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="05-merge-intervals.html"><strong aria-hidden="true">5.</strong> 5. Merge Intervals</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="06-top-k-frequent.html"><strong aria-hidden="true">6.</strong> 6. Top K Frequent Elements</a></span></li><li class="chapter-item expanded "><li class="part-title">Part II: Trees and Graphs</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="07-binary-tree.html"><strong aria-hidden="true">7.</strong> 7. Binary Tree</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="08-binary-search-tree.html"><strong aria-hidden="true">8.</strong> 8. Binary Search Tree</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="09-binary-search.html"><strong aria-hidden="true">9.</strong> 9. Binary Search on a Rotated Array</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="10-trie.html"><strong aria-hidden="true">10.</strong> 10. Trie</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="11-topological-sort.html"><strong aria-hidden="true">11.</strong> 11. Topological Sort</a></span></li><li class="chapter-item expanded "><li class="part-title">Part III: Recursion and Dynamic Programming</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="12-coin-change.html"><strong aria-hidden="true">12.</strong> 12. Coin Change</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="13-subsets.html"><strong aria-hidden="true">13.</strong> 13. Subsets</a></span></li><li class="chapter-item expanded "><li class="part-title">Part IV: Linked Structures</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="14-linked-list.html"><strong aria-hidden="true">14.</strong> 14. Reverse a Linked List</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="15-singly-linked-list.html"><strong aria-hidden="true">15.</strong> 15. Singly Linked List</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="16-doubly-linked-list.html"><strong aria-hidden="true">16.</strong> 16. Doubly Linked List</a></span></li><li class="chapter-item expanded "><li class="part-title">Part V: Caches</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="17-lru-cache.html"><strong aria-hidden="true">17.</strong> 17. LRU Cache</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="18-lru-cache-array.html"><strong aria-hidden="true">18.</strong> 18. LRU Cache, Array-Backed</a></span></li><li class="chapter-item expanded "><li class="part-title">Part VI: Concurrency and the Operating System</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="19-state-machine.html"><strong aria-hidden="true">19.</strong> 19. Workload State Machine</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="20-rate-limiter.html"><strong aria-hidden="true">20.</strong> 20. Token Bucket Rate Limiter</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="21-worker-pool.html"><strong aria-hidden="true">21.</strong> 21. Worker Pool</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="22-mutex-poisoning.html"><strong aria-hidden="true">22.</strong> 22. Mutex Poisoning</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="23-count-islands.html"><strong aria-hidden="true">23.</strong> 23. Counting Islands</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="24-syscall-overhead.html"><strong aria-hidden="true">24.</strong> 24. Syscall Overhead</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="25-shadowing.html"><strong aria-hidden="true">25.</strong> 25. Shadowing and Mutation</a></span></li><li class="chapter-item expanded "><li class="part-title">Part VII: Files, Directories, and Arguments</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="26-files-and-io.html"><strong aria-hidden="true">26.</strong> 26. Reading and Writing Files</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="27-paths-and-directories.html"><strong aria-hidden="true">27.</strong> 27. Paths and Directory Traversal</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="28-file-operations.html"><strong aria-hidden="true">28.</strong> 28. File Operations and Errors</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="29-command-line-arguments.html"><strong aria-hidden="true">29.</strong> 29. Command-Line Arguments</a></span></li><li class="chapter-item expanded "><li class="part-title">Part VIII: Coordination and Parallelism</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="30-bounded-buffer.html"><strong aria-hidden="true">30.</strong> 30. A Bounded Buffer</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="31-parallel-sum.html"><strong aria-hidden="true">31.</strong> 31. Parallel Sum</a></span></li><li class="chapter-item expanded "><li class="part-title">Part IX: Sequences, Revisited</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="32-running-median.html"><strong aria-hidden="true">32.</strong> 32. Running Median</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="33-reverse-string.html"><strong aria-hidden="true">33.</strong> 33. Reversing a String In Place</a></span></li><li class="chapter-item expanded "><li class="part-title">Part X: Reliability</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="34-idempotent-operations.html"><strong aria-hidden="true">34.</strong> 34. Idempotent Operations</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XI: Types and Pointers</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="35-adt-idioms.html"><strong aria-hidden="true">35.</strong> 35. Types That Reject Invalid Values</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="36-smart-pointers.html"><strong aria-hidden="true">36.</strong> 36. Smart Pointers and Interior Mutability</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XII: Recursion, Memory, and Caches</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="37-fibonacci.html"><strong aria-hidden="true">37.</strong> 37. Fibonacci Three Ways</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="38-list-layouts.html"><strong aria-hidden="true">38.</strong> 38. Four List Layouts and the Recursive Drop</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="39-bump-allocator.html"><strong aria-hidden="true">39.</strong> 39. A Bump Allocator</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="40-measuring-lru-layouts.html"><strong aria-hidden="true">40.</strong> 40. Measuring Two LRU Layouts</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="41-sharded-cache.html"><strong aria-hidden="true">41.</strong> 41. A Sharded Concurrent Cache</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="42-consistent-hashing.html"><strong aria-hidden="true">42.</strong> 42. Consistent Hashing</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XIII: Threads and Synchronization</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="43-threads.html"><strong aria-hidden="true">43.</strong> 43. Threads, Send, and Sync</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="44-spin-lock.html"><strong aria-hidden="true">44.</strong> 44. A Spin Lock</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="45-semaphore.html"><strong aria-hidden="true">45.</strong> 45. A Counting Semaphore</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="46-bounded-queue.html"><strong aria-hidden="true">46.</strong> 46. A Closable Bounded Queue</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="47-ring-buffer.html"><strong aria-hidden="true">47.</strong> 47. A Lock-Free Ring Buffer</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XIV: Performance and the Operating System</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="48-cache-locality.html"><strong aria-hidden="true">48.</strong> 48. Cache Locality and False Sharing</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="49-amdahl-and-deadlock.html"><strong aria-hidden="true">49.</strong> 49. Amdahl&#39;s Law and Deadlock Detection</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="50-paging-and-scheduling.html"><strong aria-hidden="true">50.</strong> 50. Paging and Round-Robin Scheduling</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XV: Networking and HTTP</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="51-ipv4-and-tcp-windows.html"><strong aria-hidden="true">51.</strong> 51. IPv4 Addresses and TCP Windows</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="52-tcp-echo-server.html"><strong aria-hidden="true">52.</strong> 52. A Thread-per-Connection Echo Server</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="53-epoll-echo-server.html"><strong aria-hidden="true">53.</strong> 53. An epoll Echo Server</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="54-http-request-parsing.html"><strong aria-hidden="true">54.</strong> 54. Parsing HTTP/1.1 Requests</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="55-http-server.html"><strong aria-hidden="true">55.</strong> 55. A Small HTTP Server</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XVI: Async Rust and Cloud Clients</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="56-async-runtime.html"><strong aria-hidden="true">56.</strong> 56. A Minimal Async Runtime</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="57-retry.html"><strong aria-hidden="true">57.</strong> 57. Retry with Backoff and Jitter</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="58-http-client.html"><strong aria-hidden="true">58.</strong> 58. An HTTP Client with Retries and Caching</a></span></li><li class="chapter-item expanded "><li class="part-title">Part XVII: Interview Drills</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="59-drills.html"><strong aria-hidden="true">59.</strong> 59. Interview Drills</a></span></li><li class="chapter-item expanded "><li class="part-title">Closing</li></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="references.html"><strong aria-hidden="true">60.</strong> References</a></span></li><li class="chapter-item expanded "><span class="chapter-link-wrapper"><a href="index.html"><strong aria-hidden="true">61.</strong> Index</a></span></li></ol>';
        // Set the current, active page, and reveal it if it's hidden
        let current_page = document.location.href.toString().split('#')[0].split('?')[0];
        if (current_page.endsWith('/')) {
            current_page += 'index.html';
        }
        const links = Array.prototype.slice.call(this.querySelectorAll('a'));
        const l = links.length;
        for (let i = 0; i < l; ++i) {
            const link = links[i];
            const href = link.getAttribute('href');
            if (href && !href.startsWith('#') && !/^(?:[a-z+]+:)?\/\//.test(href)) {
                link.href = path_to_root + href;
            }
            // The 'index' page is supposed to alias the first chapter in the book.
            // Check both with and without the '.html' suffix to be robust against pretty URLs
            if (link.href.replace(/\.html$/, '') === current_page.replace(/\.html$/, '')
                || i === 0
                && path_to_root === ''
                && current_page.endsWith('/index.html')) {
                link.classList.add('active');
                let parent = link.parentElement;
                while (parent) {
                    if (parent.tagName === 'LI' && parent.classList.contains('chapter-item')) {
                        parent.classList.add('expanded');
                    }
                    parent = parent.parentElement;
                }
            }
        }
        // Track and set sidebar scroll position
        this.addEventListener('click', e => {
            if (e.target.tagName === 'A') {
                const clientRect = e.target.getBoundingClientRect();
                const sidebarRect = this.getBoundingClientRect();
                sessionStorage.setItem('sidebar-scroll-offset', clientRect.top - sidebarRect.top);
            }
        }, { passive: true });
        const sidebarScrollOffset = sessionStorage.getItem('sidebar-scroll-offset');
        sessionStorage.removeItem('sidebar-scroll-offset');
        if (sidebarScrollOffset !== null) {
            // preserve sidebar scroll position when navigating via links within sidebar
            const activeSection = this.querySelector('.active');
            if (activeSection) {
                const clientRect = activeSection.getBoundingClientRect();
                const sidebarRect = this.getBoundingClientRect();
                const currentOffset = clientRect.top - sidebarRect.top;
                this.scrollTop += currentOffset - parseFloat(sidebarScrollOffset);
            }
        } else {
            // scroll sidebar to current active section when navigating via
            // 'next/previous chapter' buttons
            const activeSection = document.querySelector('#mdbook-sidebar .active');
            if (activeSection) {
                activeSection.scrollIntoView({ block: 'center' });
            }
        }
        // Toggle buttons
        const sidebarAnchorToggles = document.querySelectorAll('.chapter-fold-toggle');
        function toggleSection(ev) {
            ev.currentTarget.parentElement.parentElement.classList.toggle('expanded');
        }
        Array.from(sidebarAnchorToggles).forEach(el => {
            el.addEventListener('click', toggleSection);
        });
    }
}
window.customElements.define('mdbook-sidebar-scrollbox', MDBookSidebarScrollbox);


// ---------------------------------------------------------------------------
// Support for dynamically adding headers to the sidebar.

(function() {
    // This is used to detect which direction the page has scrolled since the
    // last scroll event.
    let lastKnownScrollPosition = 0;
    // This is the threshold in px from the top of the screen where it will
    // consider a header the "current" header when scrolling down.
    const defaultDownThreshold = 150;
    // Same as defaultDownThreshold, except when scrolling up.
    const defaultUpThreshold = 300;
    // The threshold is a virtual horizontal line on the screen where it
    // considers the "current" header to be above the line. The threshold is
    // modified dynamically to handle headers that are near the bottom of the
    // screen, and to slightly offset the behavior when scrolling up vs down.
    let threshold = defaultDownThreshold;
    // This is used to disable updates while scrolling. This is needed when
    // clicking the header in the sidebar, which triggers a scroll event. It
    // is somewhat finicky to detect when the scroll has finished, so this
    // uses a relatively dumb system of disabling scroll updates for a short
    // time after the click.
    let disableScroll = false;
    // Array of header elements on the page.
    let headers;
    // Array of li elements that are initially collapsed headers in the sidebar.
    // I'm not sure why eslint seems to have a false positive here.
    // eslint-disable-next-line prefer-const
    let headerToggles = [];
    // This is a debugging tool for the threshold which you can enable in the console.
    let thresholdDebug = false;

    // Updates the threshold based on the scroll position.
    function updateThreshold() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;

        // The number of pixels below the viewport, at most documentHeight.
        // This is used to push the threshold down to the bottom of the page
        // as the user scrolls towards the bottom.
        const pixelsBelow = Math.max(0, documentHeight - (scrollTop + windowHeight));
        // The number of pixels above the viewport, at least defaultDownThreshold.
        // Similar to pixelsBelow, this is used to push the threshold back towards
        // the top when reaching the top of the page.
        const pixelsAbove = Math.max(0, defaultDownThreshold - scrollTop);
        // How much the threshold should be offset once it gets close to the
        // bottom of the page.
        const bottomAdd = Math.max(0, windowHeight - pixelsBelow - defaultDownThreshold);
        let adjustedBottomAdd = bottomAdd;

        // Adjusts bottomAdd for a small document. The calculation above
        // assumes the document is at least twice the windowheight in size. If
        // it is less than that, then bottomAdd needs to be shrunk
        // proportional to the difference in size.
        if (documentHeight < windowHeight * 2) {
            const maxPixelsBelow = documentHeight - windowHeight;
            const t = 1 - pixelsBelow / Math.max(1, maxPixelsBelow);
            const clamp = Math.max(0, Math.min(1, t));
            adjustedBottomAdd *= clamp;
        }

        let scrollingDown = true;
        if (scrollTop < lastKnownScrollPosition) {
            scrollingDown = false;
        }

        if (scrollingDown) {
            // When scrolling down, move the threshold up towards the default
            // downwards threshold position. If near the bottom of the page,
            // adjustedBottomAdd will offset the threshold towards the bottom
            // of the page.
            const amountScrolledDown = scrollTop - lastKnownScrollPosition;
            const adjustedDefault = defaultDownThreshold + adjustedBottomAdd;
            threshold = Math.max(adjustedDefault, threshold - amountScrolledDown);
        } else {
            // When scrolling up, move the threshold down towards the default
            // upwards threshold position. If near the bottom of the page,
            // quickly transition the threshold back up where it normally
            // belongs.
            const amountScrolledUp = lastKnownScrollPosition - scrollTop;
            const adjustedDefault = defaultUpThreshold - pixelsAbove
                + Math.max(0, adjustedBottomAdd - defaultDownThreshold);
            threshold = Math.min(adjustedDefault, threshold + amountScrolledUp);
        }

        if (documentHeight <= windowHeight) {
            threshold = 0;
        }

        if (thresholdDebug) {
            const id = 'mdbook-threshold-debug-data';
            let data = document.getElementById(id);
            if (data === null) {
                data = document.createElement('div');
                data.id = id;
                data.style.cssText = `
                    position: fixed;
                    top: 50px;
                    right: 10px;
                    background-color: 0xeeeeee;
                    z-index: 9999;
                    pointer-events: none;
                `;
                document.body.appendChild(data);
            }
            data.innerHTML = `
                <table>
                  <tr><td>documentHeight</td><td>${documentHeight.toFixed(1)}</td></tr>
                  <tr><td>windowHeight</td><td>${windowHeight.toFixed(1)}</td></tr>
                  <tr><td>scrollTop</td><td>${scrollTop.toFixed(1)}</td></tr>
                  <tr><td>pixelsAbove</td><td>${pixelsAbove.toFixed(1)}</td></tr>
                  <tr><td>pixelsBelow</td><td>${pixelsBelow.toFixed(1)}</td></tr>
                  <tr><td>bottomAdd</td><td>${bottomAdd.toFixed(1)}</td></tr>
                  <tr><td>adjustedBottomAdd</td><td>${adjustedBottomAdd.toFixed(1)}</td></tr>
                  <tr><td>scrollingDown</td><td>${scrollingDown}</td></tr>
                  <tr><td>threshold</td><td>${threshold.toFixed(1)}</td></tr>
                </table>
            `;
            drawDebugLine();
        }

        lastKnownScrollPosition = scrollTop;
    }

    function drawDebugLine() {
        if (!document.body) {
            return;
        }
        const id = 'mdbook-threshold-debug-line';
        const existingLine = document.getElementById(id);
        if (existingLine) {
            existingLine.remove();
        }
        const line = document.createElement('div');
        line.id = id;
        line.style.cssText = `
            position: fixed;
            top: ${threshold}px;
            left: 0;
            width: 100vw;
            height: 2px;
            background-color: red;
            z-index: 9999;
            pointer-events: none;
        `;
        document.body.appendChild(line);
    }

    function mdbookEnableThresholdDebug() {
        thresholdDebug = true;
        updateThreshold();
        drawDebugLine();
    }

    window.mdbookEnableThresholdDebug = mdbookEnableThresholdDebug;

    // Updates which headers in the sidebar should be expanded. If the current
    // header is inside a collapsed group, then it, and all its parents should
    // be expanded.
    function updateHeaderExpanded(currentA) {
        // Add expanded to all header-item li ancestors.
        let current = currentA.parentElement;
        while (current) {
            if (current.tagName === 'LI' && current.classList.contains('header-item')) {
                current.classList.add('expanded');
            }
            current = current.parentElement;
        }
    }

    // Updates which header is marked as the "current" header in the sidebar.
    // This is done with a virtual Y threshold, where headers at or below
    // that line will be considered the current one.
    function updateCurrentHeader() {
        if (!headers || !headers.length) {
            return;
        }

        // Reset the classes, which will be rebuilt below.
        const els = document.getElementsByClassName('current-header');
        for (const el of els) {
            el.classList.remove('current-header');
        }
        for (const toggle of headerToggles) {
            toggle.classList.remove('expanded');
        }

        // Find the last header that is above the threshold.
        let lastHeader = null;
        for (const header of headers) {
            const rect = header.getBoundingClientRect();
            if (rect.top <= threshold) {
                lastHeader = header;
            } else {
                break;
            }
        }
        if (lastHeader === null) {
            lastHeader = headers[0];
            const rect = lastHeader.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            if (rect.top >= windowHeight) {
                return;
            }
        }

        // Get the anchor in the summary.
        const href = '#' + lastHeader.id;
        const a = [...document.querySelectorAll('.header-in-summary')]
            .find(element => element.getAttribute('href') === href);
        if (!a) {
            return;
        }

        a.classList.add('current-header');

        updateHeaderExpanded(a);
    }

    // Updates which header is "current" based on the threshold line.
    function reloadCurrentHeader() {
        if (disableScroll) {
            return;
        }
        updateThreshold();
        updateCurrentHeader();
    }


    // When clicking on a header in the sidebar, this adjusts the threshold so
    // that it is located next to the header. This is so that header becomes
    // "current".
    function headerThresholdClick(event) {
        // See disableScroll description why this is done.
        disableScroll = true;
        setTimeout(() => {
            disableScroll = false;
        }, 100);
        // requestAnimationFrame is used to delay the update of the "current"
        // header until after the scroll is done, and the header is in the new
        // position.
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                // Closest is needed because if it has child elements like <code>.
                const a = event.target.closest('a');
                const href = a.getAttribute('href');
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    threshold = targetElement.getBoundingClientRect().bottom;
                    updateCurrentHeader();
                }
            });
        });
    }

    // Takes the nodes from the given head and copies them over to the
    // destination, along with some filtering.
    function filterHeader(source, dest) {
        const clone = source.cloneNode(true);
        clone.querySelectorAll('mark').forEach(mark => {
            mark.replaceWith(...mark.childNodes);
        });
        dest.append(...clone.childNodes);
    }

    // Scans page for headers and adds them to the sidebar.
    document.addEventListener('DOMContentLoaded', function() {
        const activeSection = document.querySelector('#mdbook-sidebar .active');
        if (activeSection === null) {
            return;
        }

        const main = document.getElementsByTagName('main')[0];
        headers = Array.from(main.querySelectorAll('h2, h3, h4, h5, h6'))
            .filter(h => h.id !== '' && h.children.length && h.children[0].tagName === 'A');

        if (headers.length === 0) {
            return;
        }

        // Build a tree of headers in the sidebar.

        const stack = [];

        const firstLevel = parseInt(headers[0].tagName.charAt(1));
        for (let i = 1; i < firstLevel; i++) {
            const ol = document.createElement('ol');
            ol.classList.add('section');
            if (stack.length > 0) {
                stack[stack.length - 1].ol.appendChild(ol);
            }
            stack.push({level: i + 1, ol: ol});
        }

        // The level where it will start folding deeply nested headers.
        const foldLevel = 3;

        for (let i = 0; i < headers.length; i++) {
            const header = headers[i];
            const level = parseInt(header.tagName.charAt(1));

            const currentLevel = stack[stack.length - 1].level;
            if (level > currentLevel) {
                // Begin nesting to this level.
                for (let nextLevel = currentLevel + 1; nextLevel <= level; nextLevel++) {
                    const ol = document.createElement('ol');
                    ol.classList.add('section');
                    const last = stack[stack.length - 1];
                    const lastChild = last.ol.lastChild;
                    // Handle the case where jumping more than one nesting
                    // level, which doesn't have a list item to place this new
                    // list inside of.
                    if (lastChild) {
                        lastChild.appendChild(ol);
                    } else {
                        last.ol.appendChild(ol);
                    }
                    stack.push({level: nextLevel, ol: ol});
                }
            } else if (level < currentLevel) {
                while (stack.length > 1 && stack[stack.length - 1].level > level) {
                    stack.pop();
                }
            }

            const li = document.createElement('li');
            li.classList.add('header-item');
            li.classList.add('expanded');
            if (level < foldLevel) {
                li.classList.add('expanded');
            }
            const span = document.createElement('span');
            span.classList.add('chapter-link-wrapper');
            const a = document.createElement('a');
            span.appendChild(a);
            a.href = '#' + header.id;
            a.classList.add('header-in-summary');
            filterHeader(header.children[0], a);
            a.addEventListener('click', headerThresholdClick);
            const nextHeader = headers[i + 1];
            if (nextHeader !== undefined) {
                const nextLevel = parseInt(nextHeader.tagName.charAt(1));
                if (nextLevel > level && level >= foldLevel) {
                    const toggle = document.createElement('a');
                    toggle.classList.add('chapter-fold-toggle');
                    toggle.classList.add('header-toggle');
                    toggle.addEventListener('click', () => {
                        li.classList.toggle('expanded');
                    });
                    const toggleDiv = document.createElement('div');
                    toggleDiv.textContent = '❱';
                    toggle.appendChild(toggleDiv);
                    span.appendChild(toggle);
                    headerToggles.push(li);
                }
            }
            li.appendChild(span);

            const currentParent = stack[stack.length - 1];
            currentParent.ol.appendChild(li);
        }

        const onThisPage = document.createElement('div');
        onThisPage.classList.add('on-this-page');
        onThisPage.append(stack[0].ol);
        const activeItemSpan = activeSection.parentElement;
        activeItemSpan.after(onThisPage);
    });

    document.addEventListener('DOMContentLoaded', reloadCurrentHeader);
    document.addEventListener('scroll', reloadCurrentHeader, { passive: true });
})();

