import type { z } from "zod"

export const privateIdentityFieldNames = [
  "ipAddress",
  "email",
  "realName",
  "phoneNumber",
  "location",
  "deviceIdentifier",
  "deviceIdentifiers",
  "deviceId",
  "workplace",
  "school",
  "credential",
  "credentials",
  "inferredIdentity",
] as const

const privateIdentityFieldSet = new Set(privateIdentityFieldNames.map(normalizeFieldName))

export class PrivateIdentityFieldError extends Error {
  readonly fields: readonly string[]

  constructor(fields: readonly string[]) {
    super(`Private identity fields are not allowed: ${fields.join(", ")}`)
    this.name = "PrivateIdentityFieldError"
    this.fields = fields
  }
}

export function findPrivateIdentityFields(input: unknown): readonly string[] {
  const found = new Set<string>()
  visitUnknown(input, [], found)
  return [...found].sort()
}

export function parseBoundary<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  input: unknown,
): z.output<TSchema> {
  const privateFields = findPrivateIdentityFields(input)
  if (privateFields.length > 0) {
    throw new PrivateIdentityFieldError(privateFields)
  }
  return schema.parse(input)
}

function visitUnknown(input: unknown, path: readonly string[], found: Set<string>): void {
  if (Array.isArray(input)) {
    for (const [index, item] of input.entries()) {
      visitUnknown(item, [...path, String(index)], found)
    }
    return
  }

  if (typeof input !== "object" || input === null) {
    return
  }

  for (const [key, value] of Object.entries(input)) {
    const nextPath = [...path, key]
    if (privateIdentityFieldSet.has(normalizeFieldName(key))) {
      found.add(nextPath.join("."))
    }
    visitUnknown(value, nextPath, found)
  }
}

function normalizeFieldName(fieldName: string): string {
  return fieldName.replace(/[^a-z0-9]/gi, "").toLowerCase()
}
