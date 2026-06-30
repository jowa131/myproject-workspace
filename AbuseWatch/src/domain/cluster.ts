import type { EvidenceCluster, EvidenceRecord } from "./contracts"
import { EvidenceClusterSchema } from "./contracts"
import { evidenceTokens } from "./normalize"

export function buildEvidenceClusters(
  records: readonly EvidenceRecord[],
): readonly EvidenceCluster[] {
  const clusters: EvidenceCluster[] = []
  const byHash = new Map<string, EvidenceRecord[]>()

  for (const record of records) {
    const existing = byHash.get(record.normalizedTextHash) ?? []
    byHash.set(record.normalizedTextHash, [...existing, record])
  }

  for (const [hash, group] of byHash.entries()) {
    if (group.length >= 2) {
      clusters.push(
        EvidenceClusterSchema.parse({
          id: `cluster-exact-${hash.slice(0, 12)}`,
          kind: "exact_duplicate",
          evidenceIds: group.map((record) => record.id),
          score: 1,
          reviewerConfirmed: true,
          rationale: "Same normalized text hash.",
        }),
      )
    }
  }

  for (let leftIndex = 0; leftIndex < records.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < records.length; rightIndex += 1) {
      const left = records[leftIndex]
      const right = records[rightIndex]
      if (
        left === undefined ||
        right === undefined ||
        left.normalizedTextHash === right.normalizedTextHash
      ) {
        continue
      }
      const score = jaccardScore(
        evidenceTokens(left.originalText),
        evidenceTokens(right.originalText),
      )
      if (score >= 0.86) {
        clusters.push(
          EvidenceClusterSchema.parse({
            id: `cluster-suggestion-${left.id}-${right.id}`,
            kind: "near_duplicate_suggestion",
            evidenceIds: [left.id, right.id],
            score,
            reviewerConfirmed: false,
            rationale: `Token Jaccard ${score.toFixed(2)}; requires human review.`,
          }),
        )
      }
    }
  }

  return clusters
}

export function jaccardScore(
  leftTokens: readonly string[],
  rightTokens: readonly string[],
): number {
  if (leftTokens.length < 12 || rightTokens.length < 12) {
    return 0
  }

  const left = new Set(leftTokens)
  const right = new Set(rightTokens)
  const intersection = [...left].filter((token) => right.has(token)).length
  const union = new Set([...left, ...right]).size
  return union === 0 ? 0 : intersection / union
}
