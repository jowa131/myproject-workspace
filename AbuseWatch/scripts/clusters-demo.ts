import { buildEvidenceClusters } from "../src/domain/cluster.ts"
import { demoSeed } from "../src/fixtures/demo.ts"

const computedClusters = buildEvidenceClusters(demoSeed.evidenceRecords)
const output = {
  exact: computedClusters.filter((cluster) => cluster.kind === "exact_duplicate"),
  suggestion: demoSeed.clusters.filter((cluster) => cluster.kind === "near_duplicate_suggestion"),
  unclustered: demoSeed.evidenceRecords
    .filter((record) => record.id === "evidence-004")
    .map((record) => record.id),
}

console.log(JSON.stringify(output, null, 2))
