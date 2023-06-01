import type {TestInputDTO} from './test-input-dto';

/**
 * Generated from ai.giskard.web.dto.SuiteTestDTO
 */
export interface SuiteTestDTO {
    id: number;
    testId: string;
    testInputs: {[key: string]: TestInputDTO};
}