const { expect } = require('chai');

/**
 * @atomic-function-test
 * Template for testing atomic functions
 */
describe('atomicFunction', () => {
    // Valid input tests
    describe('valid inputs', () => {
        it('should handle basic valid case', () => {
            const result = atomicFunction({
                param: validValue
            });
            expect(result).to.equal(expectedOutput);
        });

        it('should handle edge case within valid range', () => {
            const result = atomicFunction({
                param: edgeValue
            });
            expect(result).to.equal(expectedEdgeOutput);
        });
    });

    // Invalid input tests
    describe('input validation', () => {
        it('should throw ValidationError for invalid input', () => {
            expect(() => atomicFunction({
                param: invalidValue
            })).to.throw(ValidationError);
        });

        it('should throw specific error message for invalid input', () => {
            expect(() => atomicFunction({
                param: invalidValue
            })).to.throw('Specific error message');
        });
    });

    // Edge cases and special conditions
    describe('edge cases', () => {
        it('should handle empty/null inputs', () => {
            expect(() => atomicFunction({
                param: null
            })).to.throw(ValidationError);
        });

        it('should handle boundary values', () => {
            const result = atomicFunction({
                param: boundaryValue
            });
            expect(result).to.equal(expectedBoundaryOutput);
        });
    });

    // Performance tests (if applicable)
    describe('performance', () => {
        it('should complete within expected time', () => {
            const startTime = process.hrtime();
            
            atomicFunction({
                param: validValue
            });
            
            const [seconds, nanoseconds] = process.hrtime(startTime);
            const executionTime = seconds * 1000 + nanoseconds / 1000000;
            
            expect(executionTime).to.be.below(expectedMaxTime);
        });
    });
});

// Example of a real test implementation
describe('calculateDiscount', () => {
    describe('valid inputs', () => {
        it('should calculate 20% discount correctly', () => {
            const result = calculateDiscount({
                price: 100,
                discountPercent: 20
            });
            expect(result).to.equal(80);
        });

        it('should handle zero discount', () => {
            const result = calculateDiscount({
                price: 100,
                discountPercent: 0
            });
            expect(result).to.equal(100);
        });
    });

    describe('input validation', () => {
        it('should throw error for negative price', () => {
            expect(() => calculateDiscount({
                price: -100,
                discountPercent: 20
            })).to.throw('Price must be positive');
        });

        it('should throw error for invalid discount percentage', () => {
            expect(() => calculateDiscount({
                price: 100,
                discountPercent: 101
            })).to.throw('Discount must be between 0 and 100');
        });
    });
});
