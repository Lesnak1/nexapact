import { createClient, createAccount, generatePrivateKey } from 'genlayer-js';
import { testnetBradbury, studionet, localnet } from 'genlayer-js/chains';

export type Address = `0x${string}`;

/**
 * NexaPact Protocol GenLayer Client Integration
 * Provides complete TypeScript bindings for all intelligent contract methods on GenLayer:
 * - create_agreement (Payable, locks GEN deposit, initializes agreement)
 * - add_milestone (Defines milestone specifications & evidence URL)
 * - submit_and_adjudicate_milestone (Triggers multi-validator LLM consensus against live web evidence)
 * - refund_remaining (Reclaims unapproved remaining balance)
 * - get_agreement (Read-only view of agreement state)
 * - get_milestone (Read-only view of milestone adjudication metrics & scores)
 * - get_agent_profile (Read-only view of contractor reputation score and task statistics)
 */

export const DEFAULT_NEXAPACT_ADDRESS: Address = '0x94Ea875B891902A29A5ddBA3c74e9242C875fcdd';

export interface MilestoneState {
  description: string;
  evidence_url: string;
  payout_amount: string;
  status: 'PENDING' | 'SUBMITTED' | 'APPROVED' | 'REVISION_REQUIRED' | 'REFUNDED';
  score_functional: number;
  score_criteria: number;
  score_quality: number;
  defect_severity: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  adjudication_summary: string;
}

export interface EscrowAgreementState {
  client: string;
  contractor: string;
  total_locked: string;
  remaining_balance: string;
  is_active: boolean;
  milestone_count: number;
  title: string;
}

export interface AgentProfileState {
  reputation_score: number;
  completed_tasks: number;
  slashed_tasks: number;
  metadata_uri: string;
}

export type SupportedChain = 'testnetBradbury' | 'studionet' | 'localnet';

export function getChainConfig(chainType: SupportedChain = 'testnetBradbury') {
  switch (chainType) {
    case 'studionet':
      return studionet;
    case 'localnet':
      return localnet;
    case 'testnetBradbury':
    default:
      return testnetBradbury;
  }
}

export function getGenLayerClient(
  privateKey?: `0x${string}`,
  chainType: SupportedChain = 'testnetBradbury'
) {
  const account = privateKey ? createAccount(privateKey) : createAccount(generatePrivateKey());
  const chain = getChainConfig(chainType);

  return createClient({
    chain,
    account,
  });
}

/**
 * Creates an escrow agreement and locks deposited GEN funds.
 */
export async function createAgreement(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  contractorAddress: Address,
  depositGenAmount: string | number,
  title: string = 'Agent Labor Agreement'
): Promise<`0x${string}`> {
  const depositWei = BigInt(Math.floor(Number(depositGenAmount) * 1e18));

  const txHash = await client.writeContract({
    address: contractAddress,
    functionName: 'create_agreement',
    args: [contractorAddress, title],
    value: depositWei,
  });

  return txHash as `0x${string}`;
}

/**
 * Client defines and adds a verifiable milestone to the agreement.
 */
export async function addMilestone(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agreementId: bigint | number,
  description: string,
  evidenceUrl: string,
  payoutGenAmount: string | number
): Promise<`0x${string}`> {
  const payoutWei = BigInt(Math.floor(Number(payoutGenAmount) * 1e18));

  const txHash = await client.writeContract({
    address: contractAddress,
    functionName: 'add_milestone',
    args: [BigInt(agreementId), description, evidenceUrl, payoutWei],
    value: 0n,
  });

  return txHash as `0x${string}`;
}

/**
 * Contractor submits evidence URL and triggers multi-validator LLM consensus.
 */
export async function submitAndAdjudicateMilestone(
  contractorClient: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agreementId: bigint | number,
  milestoneIdx: number,
  submissionNotes: string = ''
): Promise<`0x${string}`> {
  const txHash = await contractorClient.writeContract({
    address: contractAddress,
    functionName: 'submit_and_adjudicate_milestone',
    args: [BigInt(agreementId), milestoneIdx, submissionNotes],
    value: 0n,
  });

  return txHash as `0x${string}`;
}

/**
 * Client reclaims unreleased funds.
 */
export async function refundRemaining(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agreementId: bigint | number
): Promise<`0x${string}`> {
  const txHash = await client.writeContract({
    address: contractAddress,
    functionName: 'refund_remaining',
    args: [BigInt(agreementId)],
    value: 0n,
  });

  return txHash as `0x${string}`;
}

/**
 * Reads agreement state from GenLayer RPC.
 */
export async function getAgreement(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agreementId: bigint | number
): Promise<EscrowAgreementState> {
  const result = await client.readContract({
    address: contractAddress,
    functionName: 'get_agreement',
    args: [BigInt(agreementId)],
  });

  return result as unknown as EscrowAgreementState;
}

/**
 * Reads milestone adjudication scores and status from GenLayer RPC.
 */
export async function getMilestone(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agreementId: bigint | number,
  milestoneIdx: number
): Promise<MilestoneState> {
  const result = await client.readContract({
    address: contractAddress,
    functionName: 'get_milestone',
    args: [BigInt(agreementId), milestoneIdx],
  });

  return result as unknown as MilestoneState;
}

/**
 * Reads agent reputation profile from GenLayer RPC.
 */
export async function getAgentProfile(
  client: ReturnType<typeof getGenLayerClient>,
  contractAddress: Address,
  agentAddress: Address
): Promise<AgentProfileState> {
  const result = await client.readContract({
    address: contractAddress,
    functionName: 'get_agent_profile',
    args: [agentAddress],
  });

  return result as unknown as AgentProfileState;
}
