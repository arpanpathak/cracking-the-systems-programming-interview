// Command cas builds a small content-addressed store for model artifacts and
// runs it through the situations such a store exists for.
//
// A blob is stored under the SHA-256 digest of its bytes. An artifact is cut
// into chunks, each chunk is a blob, and a manifest lists the chunks. The
// program pushes two versions of a model that differ in their last quarter,
// pulls the second to a machine that has the first, corrupts one stored
// chunk, and removes what nothing refers to any more.
//
// Run it from code/go with:
//
//	go run ./cas
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
)

// ANCHOR: store
// Digest names a blob: "sha256:" followed by the hash of its bytes in hex.
type Digest string

// digestOf computes the name of some bytes.
func digestOf(data []byte) Digest {
	sum := sha256.Sum256(data)
	return Digest("sha256:" + hex.EncodeToString(sum[:]))
}

// short returns the first twelve hex digits, for printing.
func (d Digest) short() string { return string(d)[:19] }

// Store holds blobs by digest and tags by name.
type Store struct {
	// blobs maps each digest to the bytes it names.
	blobs map[Digest][]byte
	// tags maps a name people use, such as "llm:v1", to a manifest's digest.
	tags map[string]Digest
}

// NewStore returns an empty store.
func NewStore() *Store {
	return &Store{blobs: map[Digest][]byte{}, tags: map[string]Digest{}}
}

// Put stores a blob and returns its digest and whether it was new. Bytes the
// store already holds are not stored a second time.
func (s *Store) Put(data []byte) (Digest, bool) {
	d := digestOf(data)
	if _, held := s.blobs[d]; held {
		return d, false
	}
	s.blobs[d] = data
	return d, true
}

// ErrCorrupt is returned when a blob's bytes no longer match its name.
var ErrCorrupt = errors.New("contents do not match the digest")

// Get returns a blob after checking that its bytes still hash to its name.
func (s *Store) Get(d Digest) ([]byte, error) {
	data, held := s.blobs[d]
	if !held {
		return nil, fmt.Errorf("%s: not found", d.short())
	}
	if digestOf(data) != d {
		return nil, fmt.Errorf("%s: %w", d.short(), ErrCorrupt)
	}
	return data, nil
}

// ANCHOR_END: store

// ANCHOR: push
// chunkSize is the size of the pieces an artifact is cut into.
const chunkSize = 8 * 1024

// Push cuts an artifact into chunks, stores each chunk, stores a manifest
// that lists the chunks' digests in order, and points the tag at the
// manifest. It returns how many chunks were new to the store.
func (s *Store) Push(tag string, artifact []byte) (manifest Digest, chunks, added int) {
	var lines strings.Builder
	for start := 0; start < len(artifact); start += chunkSize {
		chunk := artifact[start:min(start+chunkSize, len(artifact))]
		d, fresh := s.Put(chunk)
		if fresh {
			added++
		}
		chunks++
		fmt.Fprintf(&lines, "%s %d\n", d, len(chunk))
	}
	manifest, _ = s.Put([]byte(lines.String()))
	s.tags[tag] = manifest
	return manifest, chunks, added
}

// chunksOf reads a manifest and returns the digests it lists.
func (s *Store) chunksOf(manifest Digest) ([]Digest, error) {
	data, err := s.Get(manifest)
	if err != nil {
		return nil, err
	}
	var out []Digest
	for line := range strings.Lines(string(data)) {
		digest, _, _ := strings.Cut(line, " ")
		out = append(out, Digest(digest))
	}
	return out, nil
}

// ANCHOR_END: push

// ANCHOR: pull
// Pull copies a tagged artifact from a remote store into this one, fetching
// only the chunks this store does not hold. It returns the number of chunks
// and bytes fetched.
func (s *Store) Pull(remote *Store, tag string) (fetched, bytes int, err error) {
	manifest := remote.tags[tag]
	chunks, err := remote.chunksOf(manifest)
	if err != nil {
		return 0, 0, err
	}
	for _, d := range chunks {
		if _, held := s.blobs[d]; held {
			continue
		}
		data, err := remote.Get(d)
		if err != nil {
			return fetched, bytes, err
		}
		s.blobs[d] = data
		fetched++
		bytes += len(data)
	}
	data, _ := remote.Get(manifest)
	s.blobs[manifest] = data
	s.tags[tag] = manifest
	return fetched, bytes, nil
}

// Read reassembles a tagged artifact, verifying every chunk on the way.
func (s *Store) Read(tag string) ([]byte, error) {
	chunks, err := s.chunksOf(s.tags[tag])
	if err != nil {
		return nil, err
	}
	var artifact []byte
	for i, d := range chunks {
		data, err := s.Get(d)
		if err != nil {
			return nil, fmt.Errorf("chunk %d: %w", i, err)
		}
		artifact = append(artifact, data...)
	}
	return artifact, nil
}

// ANCHOR_END: pull

// ANCHOR: gc
// Collect removes every blob that no tag leads to. It first marks the
// manifests the tags name and the chunks those manifests list, then sweeps
// the rest. It returns the number of blobs and bytes removed.
func (s *Store) Collect() (removed, bytes int) {
	live := map[Digest]bool{}
	for _, manifest := range s.tags {
		live[manifest] = true
		chunks, _ := s.chunksOf(manifest)
		for _, d := range chunks {
			live[d] = true
		}
	}
	for d, data := range s.blobs {
		if !live[d] {
			removed++
			bytes += len(data)
			delete(s.blobs, d)
		}
	}
	return removed, bytes
}

// ANCHOR_END: gc

// size returns the number of blobs in a store and their total size.
func (s *Store) size() (blobs, bytes int) {
	for _, data := range s.blobs {
		bytes += len(data)
	}
	return len(s.blobs), bytes
}

// weights returns n bytes that stand for a model's weights. The bytes come
// from a fixed sequence, so every run and both languages produce the same.
func weights(n int, seed uint32) []byte {
	out := make([]byte, n)
	x := seed
	for i := range out {
		x = x*1664525 + 1013904223
		out[i] = byte(x >> 24)
	}
	return out
}

// ANCHOR: main
func main() {
	// Version 1 is 64 KiB. Version 2 is a fine-tuned copy: the first three
	// quarters are unchanged and the last quarter is new.
	v1 := weights(64*1024, 1)
	v2 := append(append([]byte{}, v1[:48*1024]...), weights(16*1024, 2)...)

	registry := NewStore()
	m1, chunks, added := registry.Push("llm:v1", v1)
	fmt.Printf("push llm:v1: %d chunks, %d new; manifest %s\n", chunks, added, m1.short())
	m2, chunks, added := registry.Push("llm:v2", v2)
	fmt.Printf("push llm:v2: %d chunks, %d new; manifest %s\n", chunks, added, m2.short())
	blobs, bytes := registry.size()
	fmt.Printf("the registry holds %d blobs and %d bytes for %d bytes of artifacts\n", blobs, bytes, len(v1)+len(v2))

	node := NewStore()
	fetched, n, _ := node.Pull(registry, "llm:v1")
	fmt.Printf("thor-1 pulls llm:v1: %d chunks fetched, %d bytes\n", fetched, n)
	fetched, n, _ = node.Pull(registry, "llm:v2")
	fmt.Printf("thor-1 pulls llm:v2: %d chunks fetched, %d bytes\n", fetched, n)

	fmt.Println("one bit flips in a chunk stored on thor-1:")
	chunkList, _ := node.chunksOf(node.tags["llm:v1"])
	damaged := append([]byte{}, node.blobs[chunkList[3]]...)
	damaged[100] ^= 1
	node.blobs[chunkList[3]] = damaged
	if _, err := node.Read("llm:v1"); err != nil {
		fmt.Printf("  read llm:v1: %v\n", err)
	}
	// The bad chunk is dropped and pulled again, by name, from the registry.
	delete(node.blobs, chunkList[3])
	fetched, n, _ = node.Pull(registry, "llm:v1")
	fmt.Printf("  thor-1 drops the chunk and pulls llm:v1 again: %d chunk fetched, %d bytes\n", fetched, n)
	if got, err := node.Read("llm:v1"); err == nil {
		fmt.Printf("  read llm:v1: %d bytes, digest %s\n", len(got), digestOf(got).short())
	}

	fmt.Println("the tag llm:v1 is deleted from the registry:")
	delete(registry.tags, "llm:v1")
	removed, n := registry.Collect()
	blobs, bytes = registry.size()
	fmt.Printf("  collected %d blobs, %d bytes; %d blobs and %d bytes remain\n", removed, n, blobs, bytes)
}

// ANCHOR_END: main
